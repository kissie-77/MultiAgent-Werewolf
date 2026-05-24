"""LLM 输出、AgentScope Agent 与游戏引擎之间的统一适配层。

所有基于座位的决策、结构化输出解析与 Agent 调用应经本模块
（通过 InformationHub / PhaseInteraction）完成。
后续扩展（如信念矩阵）可在此添加决策模型并接入下方 request_* 方法。
"""

from __future__ import annotations

import json
import re
import random
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from llm_werewolf.strategy.role_prompts import GamePrompts, ROLE_SEAT_ACTION
from llm_werewolf.agent_team.structured_invoke import (
    agent_uses_structured_output,
    coerce_speech,
    invoke_structured,
)
from llm_werewolf.core.decisions import (
    GENERATE_RESPONSE_INSTRUCTION,
    MultiSeatChoiceDecision,
    SeatChoiceDecision,
    SpeechDecision,
    VoteIntentionDecision,
    WitchNightDecision,
    YesNoDecision,
    extract_public_text,
    is_valid_public_speech,
    normalize_speech_decision,
    seat_choice_schema_instruction,
    speech_schema_instruction,
    vote_intention_schema_instruction,
    witch_night_schema_instruction,
)
from llm_werewolf.core.vote_intention import VoteIntentionAnchor, VoteIntentionEntry
from llm_werewolf.core.phase_outputs import ActionPhase, RoundtablePhase, action_phase_instruction
from llm_werewolf.core.types import AgentProtocol, PlayerProtocol

if TYPE_CHECKING:
    pass


class WerewolfAdapterBridge:
    """解析 LLM 回复并驱动 AgentProtocol / AgentScope Agent。"""

    # ------------------------------------------------------------------
    # 座位辅助（全局编号：player_N → 座位 N）
    # ------------------------------------------------------------------

    @staticmethod
    def get_player_seat(player: PlayerProtocol) -> int | None:
        """返回玩家稳定的 1 基座位号。"""
        for value in (player.player_id, player.name):
            match = re.search(r"(\d+)$", str(value))
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def resolve_player_by_seat(
        seat: int,
        candidates: list[PlayerProtocol],
    ) -> PlayerProtocol | None:
        """在候选列表中按座位号匹配玩家。"""
        for player in candidates:
            if WerewolfAdapterBridge.get_player_seat(player) == seat:
                return player
        return None

    # ------------------------------------------------------------------
    # 解析（文本 / 结构化 → 引擎语义）
    # ------------------------------------------------------------------

    @staticmethod
    def parse_target_selection(
        response: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool = False,
    ) -> PlayerProtocol | None:
        if allow_skip and re.search(r"\bskip\b", response, flags=re.I):
            return None

        numbers = re.findall(r"\d+", response.strip())
        if not numbers:
            return None

        try:
            seat = int(numbers[0])
            if allow_skip and seat == 0:
                return None
            return WerewolfAdapterBridge.resolve_player_by_seat(seat, possible_targets)
        except (ValueError, IndexError):
            return None

    @staticmethod
    def parse_yes_no(response: str) -> bool:
        response_lower = response.strip().lower()
        bracketed_number = re.search(r"\[\[\s*([01])\s*\]\]", response)
        if bracketed_number:
            return bracketed_number.group(1) == "1"
        if re.fullmatch(r"\s*[01]\s*", response):
            return response.strip() == "1"
        if "no" in response_lower or "否" in response_lower or "不" in response_lower:
            return False
        return "yes" in response_lower or "是" in response_lower

    @staticmethod
    def parse_multi_target_selection(
        response: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
    ) -> list[PlayerProtocol] | None:
        numbers = re.findall(r"\d+", response.strip())
        if len(numbers) != num_targets:
            return None

        try:
            selected: list[PlayerProtocol] = []
            for num_str in numbers:
                seat = int(num_str)
                target = WerewolfAdapterBridge.resolve_player_by_seat(seat, possible_targets)
                if target is None:
                    return None
                selected.append(target)

            if len(selected) != len({p.player_id for p in selected}):
                return None
            return selected
        except (ValueError, IndexError):
            return None

    @staticmethod
    def parse_speech(response: str) -> SpeechDecision:
        """将模型原始文本拆分为公开发言与私人推理。"""
        private_blocks = re.findall(r"\{([^}]*)\}", response, flags=re.S)
        private_thought = "\n".join(b.strip() for b in private_blocks if b.strip()) or None
        decision = SpeechDecision.model_construct(
            public_speech=extract_public_text(response),
            private_thought=private_thought,
        )
        return normalize_speech_decision(decision, raw_fallback=response)

    # ------------------------------------------------------------------
    # Prompt 构建（引擎 → LLM）
    # ------------------------------------------------------------------

    @staticmethod
    def build_target_selection_prompt(
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool = False,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
        *,
        structured: bool = False,
        action_phase: ActionPhase | None = None,
    ) -> str:
        prompt_parts = [f"你是{role_name}。"]

        if round_number is not None and phase:
            prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")
        elif round_number is not None:
            prompt_parts.append(f"当前回合：{round_number}")

        prompt_parts.extend([f"任务：{action_description}", ""])

        if additional_context:
            prompt_parts.extend([additional_context, ""])

        prompt_parts.append("可选目标：")
        for target in possible_targets:
            seat = WerewolfAdapterBridge.get_player_seat(target)
            seat_label = seat if seat is not None else target.player_id
            prompt_parts.append(
                f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）"
            )

        if allow_skip:
            prompt_parts.append("- 座位 0：跳过（不执行此行动）")

        action_line = ROLE_SEAT_ACTION.get(role_name, GamePrompts.PROPHET_ACTION)
        prompt_parts.extend(["", action_line])
        if action_phase is not None:
            prompt_parts.extend(["", action_phase_instruction(action_phase)])
        if structured:
            prompt_parts.extend(["", seat_choice_schema_instruction(allow_skip=allow_skip)])
        else:
            prompt_parts.extend([
                "",
                "请只回复目标玩家的全局座位号，放在 [[数字]] 中。",
                "使用真实座位号，不是列表序号。不要输出其他文字。",
            ])
        return "\n".join(prompt_parts)

    @staticmethod
    def build_yes_no_prompt(
        role_name: str,
        question: str,
        context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
        *,
        structured: bool = False,
    ) -> str:
        prompt_parts = [f"你是{role_name}。"]

        if round_number is not None and phase:
            prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")
        elif round_number is not None:
            prompt_parts.append(f"当前回合：{round_number}")

        prompt_parts.append(f"问题：{question}")

        if context:
            prompt_parts.extend(["", context])

        if structured:
            prompt_parts.extend([
                "",
                "请调用 generate_response：choice=true 表示是，false 表示否。",
                GENERATE_RESPONSE_INSTRUCTION,
            ])
        else:
            prompt_parts.extend([
                "",
                "请只回复 [[1]] 表示是，[[0]] 表示否。不要输出其他文字。",
            ])
        return "\n".join(prompt_parts)

    @staticmethod
    def build_multi_target_prompt(
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
        *,
        structured: bool = False,
    ) -> str:
        prompt_parts = [f"你是{role_name}。"]

        if round_number is not None and phase:
            prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")
        elif round_number is not None:
            prompt_parts.append(f"当前回合：{round_number}")

        prompt_parts.extend([
            f"任务：{action_description}",
            f"请选择 {num_targets} 个不同目标。",
            "",
        ])

        if additional_context:
            prompt_parts.extend([additional_context, ""])

        prompt_parts.append("可选目标：")
        for target in possible_targets:
            seat = WerewolfAdapterBridge.get_player_seat(target)
            seat_label = seat if seat is not None else target.player_id
            prompt_parts.append(
                f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）"
            )

        if structured:
            prompt_parts.extend([
                "",
                f"请调用 generate_response，在 seats 字段填写 {num_targets} 个互不重复的全局座位号。",
                GENERATE_RESPONSE_INSTRUCTION,
            ])
        else:
            prompt_parts.extend([
                "",
                f"请回复 {num_targets} 个全局座位号，用逗号分隔，例如：1, 3",
                "使用真实座位号，不是列表序号。",
            ])
        return "\n".join(prompt_parts)

    @staticmethod
    def build_speech_prompt(
        context: str,
        instruction: str = "",
        *,
        structured: bool = True,
        roundtable_phase: RoundtablePhase | None = None,
    ) -> str:
        from llm_werewolf.core.phase_outputs import roundtable_phase_instruction

        parts = [context]
        if instruction:
            parts.extend(["", instruction])
        parts.extend(["", GamePrompts.SPEECH_PROMPT])
        if roundtable_phase is not None:
            parts.extend(["", roundtable_phase_instruction(roundtable_phase)])
        elif structured:
            parts.extend(["", speech_schema_instruction()])
        else:
            parts.extend([
                "",
                speech_schema_instruction(),
                "（兼容模式）若无法调用工具，可用 [[完整中文发言]] 与 {...} 私人推理，",
                "引擎将尽量解析为 SpeechDecision。",
            ])
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Agent 调用（generate_response → Msg.metadata；旧版文本兜底）
    # ------------------------------------------------------------------

    @staticmethod
    def _store_decision_metadata(
        agent: AgentProtocol,
        target: PlayerProtocol | None,
        *,
        response: str | None = None,
        decision: BaseModel | None = None,
        fallback: bool = False,
    ) -> None:
        if target is None:
            return

        metadata: dict[str, Any] = {
            "decision_seat": WerewolfAdapterBridge.get_player_seat(target),
            "resolved_target_id": target.player_id,
            "resolved_target_name": target.name,
            "fallback": fallback,
        }
        if response is not None:
            metadata["raw_response"] = response
        if decision is not None:
            metadata["structured_decision"] = decision.model_dump(mode="json")

        object.__setattr__(agent, "_last_decision_metadata", metadata)

    @staticmethod
    @staticmethod
    def build_witch_night_prompt(
        role_name: str,
        *,
        can_see_victim: bool,
        victim_line: str,
        poison_targets: list[PlayerProtocol],
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
        structured: bool = False,
    ) -> str:
        prompt_parts = [f"你是{role_name}。", GamePrompts.WITCH_OPEN, ""]

        if round_number is not None and phase:
            prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")

        if can_see_victim and victim_line:
            prompt_parts.extend(["", victim_line])
        elif not can_see_victim:
            prompt_parts.extend([
                "",
                "你的解药已用完，系统不会告知今晚狼人刀口是谁。",
            ])

        if additional_context:
            prompt_parts.extend(["", additional_context, ""])

        if poison_targets:
            prompt_parts.append("若选择 poison，可选毒杀目标：")
            for target in poison_targets:
                seat = WerewolfAdapterBridge.get_player_seat(target)
                seat_label = seat if seat is not None else target.player_id
                prompt_parts.append(
                    f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）"
                )

        prompt_parts.extend([
            "",
            "请在本回合三选一：救人(save) / 毒人(poison) / 不行动(none)。",
            "救人仅当仍有解药且本提示给出了刀口目标；毒人需指定 seat。",
        ])
        prompt_parts.extend(["", action_phase_instruction(ActionPhase.WITCH_NIGHT)])
        if structured:
            prompt_parts.extend([
                "",
                witch_night_schema_instruction(can_see_victim=can_see_victim),
            ])
        return "\n".join(prompt_parts)

    @staticmethod
    async def request_witch_night_choice(
        agent: AgentProtocol,
        role_name: str,
        *,
        can_see_victim: bool,
        victim_line: str,
        poison_targets: list[PlayerProtocol],
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> WitchNightDecision:
        """返回女巫夜间决策；失败时默认为 none。"""
        structured = agent_uses_structured_output(agent)
        prompt = WerewolfAdapterBridge.build_witch_night_prompt(
            role_name,
            can_see_victim=can_see_victim,
            victim_line=victim_line,
            poison_targets=poison_targets,
            additional_context=additional_context,
            round_number=round_number,
            phase=phase,
            structured=structured,
        )
        default = WitchNightDecision(action="none", seat=0, reason=None)
        try:
            if structured:
                result = await invoke_structured(agent, prompt, WitchNightDecision)
                if isinstance(result, WitchNightDecision):
                    WerewolfAdapterBridge._store_decision_metadata(
                        agent, None, decision=result
                    )
                    return result
            response = await agent.get_response(prompt)
            lowered = response.lower()
            if "save" in lowered or "救" in response:
                return WitchNightDecision(action="save", seat=0, reason=response[:200])
            if "poison" in lowered or "毒" in response:
                seat_match = re.search(r"\[\[\s*(\d+)\s*\]\]", response)
                seat = int(seat_match.group(1)) if seat_match else 0
                return WitchNightDecision(action="poison", seat=seat, reason=response[:200])
        except Exception:
            pass
        return default

    @staticmethod
    def build_vote_intention_entry(
        player: PlayerProtocol,
        seat: int,
        possible_targets: list[PlayerProtocol],
        reason: str | None,
    ) -> VoteIntentionEntry:
        target = (
            WerewolfAdapterBridge.resolve_player_by_seat(seat, possible_targets)
            if seat > 0
            else None
        )
        return VoteIntentionEntry(
            player_id=player.player_id,
            player_name=player.name,
            seat=seat,
            target_id=target.player_id if target else None,
            target_name=target.name if target else None,
            reason=reason,
        )

    @staticmethod
    def build_vote_intention_prompt(
        role_name: str,
        possible_targets: list[PlayerProtocol],
        additional_context: str,
        *,
        anchor: VoteIntentionAnchor,
        last_speaker_name: str | None = None,
        round_number: int | None = None,
        phase: str | None = None,
        structured: bool = False,
    ) -> str:
        if anchor == VoteIntentionAnchor.INITIAL:
            situation = (
                "本轮讨论刚刚开始，尚无人发言。"
                "请上报你此刻若进行放逐投票会投给谁。"
            )
        else:
            situation = (
                f"你刚听完 {last_speaker_name or '上一位玩家'} 的发言（已写入对话记忆）。"
                "请根据最新讨论更新：若此刻投票会放逐谁？"
            )
        prompt_parts = [
            f"你是{role_name}。",
            "",
            "【投票意向采集 · 非正式投票】",
            situation,
            "你必须明确给出意向：有目标填 seat=全局座位号；观望/无明确目标填 seat=0。",
            "seat=0 也必须由你主动选择，不可省略回复。",
        ]
        if round_number is not None and phase:
            prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")

        if additional_context:
            prompt_parts.extend(["", additional_context, ""])

        if possible_targets:
            prompt_parts.append("可选放逐目标（全局座位号）：")
            for target in possible_targets:
                seat = WerewolfAdapterBridge.get_player_seat(target)
                seat_label = seat if seat is not None else "?"
                prompt_parts.append(
                    f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）"
                )

        prompt_parts.extend([
            "",
            action_phase_instruction(ActionPhase.VOTE_INTENTION),
        ])
        if structured:
            prompt_parts.extend(["", vote_intention_schema_instruction()])
        return "\n".join(prompt_parts)

    @staticmethod
    async def request_vote_intention(
        agent: AgentProtocol,
        role_name: str,
        actor: PlayerProtocol,
        possible_targets: list[PlayerProtocol],
        additional_context: str,
        *,
        anchor: VoteIntentionAnchor,
        last_speaker_name: str | None = None,
        round_number: int | None = None,
        phase: str | None = None,
    ) -> VoteIntentionEntry:
        """采集一名玩家的投票意向；始终调用模型（seat=0 表示明确无意向）。"""
        structured = agent_uses_structured_output(agent)
        prompt = WerewolfAdapterBridge.build_vote_intention_prompt(
            role_name,
            possible_targets,
            additional_context,
            anchor=anchor,
            last_speaker_name=last_speaker_name,
            round_number=round_number,
            phase=phase,
            structured=structured,
        )

        def _entry_from_seat(seat: int, reason: str | None) -> VoteIntentionEntry:
            safe_seat = max(0, int(seat))
            if safe_seat > 0 and WerewolfAdapterBridge.resolve_player_by_seat(
                safe_seat, possible_targets
            ) is None:
                safe_seat = 0
            return WerewolfAdapterBridge.build_vote_intention_entry(
                actor, safe_seat, possible_targets, reason
            )

        last_error: str | None = None
        if structured:
            try:
                result = await invoke_structured(agent, prompt, VoteIntentionDecision)
                if isinstance(result, VoteIntentionDecision):
                    return _entry_from_seat(result.seat, result.reason)
            except Exception as exc:
                last_error = str(exc)

        try:
            response = await agent.get_response(prompt)
        except Exception as exc:
            msg = f"vote_intention LLM failed: {last_error or exc}"
            raise RuntimeError(msg) from exc

        target = WerewolfAdapterBridge.parse_target_selection(
            response, possible_targets, allow_skip=True
        )
        if target is not None:
            seat = WerewolfAdapterBridge.get_player_seat(target) or 0
            return _entry_from_seat(seat, response[:500])

        numbers = re.findall(r"\[\[\s*(\d+)\s*\]\]", response)
        if numbers:
            return _entry_from_seat(int(numbers[0]), response[:500])
        loose = re.findall(r"\d+", response.strip())
        if loose:
            return _entry_from_seat(int(loose[0]), response[:500])
        return _entry_from_seat(0, response[:500] or "seat=0（模型明示无意向）")

    @staticmethod
    async def request_seat_choice(
        agent: AgentProtocol,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool = False,
        additional_context: str = "",
        fallback_random: bool = True,
        round_number: int | None = None,
        phase: str | None = None,
        action_phase: ActionPhase | None = None,
    ) -> PlayerProtocol | None:
        if not possible_targets:
            return None

        structured = agent_uses_structured_output(agent)
        prompt = WerewolfAdapterBridge.build_target_selection_prompt(
            role_name,
            action_description,
            possible_targets,
            allow_skip,
            additional_context,
            round_number,
            phase,
            structured=structured,
            action_phase=action_phase,
        )

        try:
            if structured:
                result = await invoke_structured(agent, prompt, SeatChoiceDecision)
                if isinstance(result, SeatChoiceDecision):
                    if allow_skip and result.seat == 0:
                        WerewolfAdapterBridge._store_decision_metadata(
                            agent, None, decision=result
                        )
                        return None
                    target = WerewolfAdapterBridge.resolve_player_by_seat(
                        result.seat, possible_targets
                    )
                    if target is not None:
                        WerewolfAdapterBridge._store_decision_metadata(
                            agent, target, decision=result
                        )
                        return target
                response = await agent.get_response(prompt)
                target = WerewolfAdapterBridge.parse_target_selection(
                    response, possible_targets, allow_skip
                )
                if target is not None or allow_skip:
                    WerewolfAdapterBridge._store_decision_metadata(
                        agent, target, response=response
                    )
                    return target
            else:
                response = await agent.get_response(prompt)
                target = WerewolfAdapterBridge.parse_target_selection(
                    response, possible_targets, allow_skip
                )
                if target is not None or allow_skip:
                    WerewolfAdapterBridge._store_decision_metadata(
                        agent, target, response=response
                    )
                    return target

            if fallback_random:
                target = random.choice(possible_targets)  # noqa: S311
                WerewolfAdapterBridge._store_decision_metadata(
                    agent, target, fallback=True
                )
                return target
        except Exception:
            if fallback_random:
                target = random.choice(possible_targets)  # noqa: S311
                WerewolfAdapterBridge._store_decision_metadata(agent, target, fallback=True)
                return target

        return None

    @staticmethod
    async def request_yes_no(
        agent: AgentProtocol,
        role_name: str,
        question: str,
        context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> bool:
        structured = agent_uses_structured_output(agent)
        prompt = WerewolfAdapterBridge.build_yes_no_prompt(
            role_name,
            question,
            context,
            round_number,
            phase,
            structured=structured,
        )
        try:
            if structured:
                result = await invoke_structured(agent, prompt, YesNoDecision)
                if isinstance(result, YesNoDecision):
                    return result.choice
                response = await agent.get_response(prompt)
                return WerewolfAdapterBridge.parse_yes_no(response)
            response = await agent.get_response(prompt)
            return WerewolfAdapterBridge.parse_yes_no(response)
        except Exception:
            pass
        return False

    @staticmethod
    async def request_multi_target(
        agent: AgentProtocol,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> list[PlayerProtocol] | None:
        if not possible_targets or num_targets < 1:
            return None

        structured = agent_uses_structured_output(agent)
        prompt = WerewolfAdapterBridge.build_multi_target_prompt(
            role_name,
            action_description,
            possible_targets,
            num_targets,
            additional_context,
            round_number,
            phase,
            structured=structured,
        )

        try:
            if structured:
                result = await invoke_structured(
                    agent, prompt, MultiSeatChoiceDecision
                )
                if isinstance(result, MultiSeatChoiceDecision):
                    selected: list[PlayerProtocol] = []
                    for seat in result.seats:
                        player = WerewolfAdapterBridge.resolve_player_by_seat(
                            seat, possible_targets
                        )
                        if player is None:
                            return None
                        selected.append(player)
                    if len(selected) == len({p.player_id for p in selected}):
                        return selected
            else:
                response = await agent.get_response(prompt)
                return WerewolfAdapterBridge.parse_multi_target_selection(
                    response, possible_targets, num_targets
                )
        except Exception:
            pass
        return None

    @staticmethod
    async def request_speech(
        agent: AgentProtocol,
        context: str,
        instruction: str = "",
        *,
        schema_retries: int = 3,
        roundtable_phase: RoundtablePhase | None = None,
    ) -> SpeechDecision:
        structured = agent_uses_structured_output(agent)
        prompt = WerewolfAdapterBridge.build_speech_prompt(
            context,
            instruction,
            structured=structured,
            roundtable_phase=roundtable_phase,
        )
        try:
            if structured:
                for _ in range(schema_retries):
                    result = await invoke_structured(
                        agent, prompt, SpeechDecision, retries=1
                    )
                    if result is not None:
                        speech = coerce_speech(result)
                        if is_valid_public_speech(speech.public_speech):
                            return speech
                response = await agent.get_response(prompt)
                parsed = WerewolfAdapterBridge.parse_speech(response)
                if is_valid_public_speech(parsed.public_speech):
                    return parsed
            else:
                response = await agent.get_response(prompt)
                parsed = WerewolfAdapterBridge.parse_speech(response)
                if is_valid_public_speech(parsed.public_speech):
                    return parsed
        except Exception:
            pass
        fallback_getter = getattr(agent, "_generate_fallback_response", None)
        if callable(fallback_getter):
            raw = fallback_getter(prompt, "speech_fallback")
            parsed = WerewolfAdapterBridge.parse_speech(raw)
            if is_valid_public_speech(parsed.public_speech):
                return parsed
        return SpeechDecision(
            public_speech="（无公开发言）",
            private_thought=None,
        )
