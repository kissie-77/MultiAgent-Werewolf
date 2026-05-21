"""Unified adapter between LLM output, AgentScope agents, and the game engine.

All seat-based decisions, structured output parsing, and agent invocation should
go through this module (via InformationHub / PhaseInteraction).
Future extensions (e.g. belief matrices) add decision models here and wire
request_* methods below.
"""

from __future__ import annotations

import re
import random
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from llm_werewolf.adapter.prompts import GamePrompts, ROLE_SEAT_ACTION
from llm_werewolf.adapter.structured_invoke import (
    agent_uses_structured_output,
    coerce_speech,
    invoke_structured,
)
from llm_werewolf.core.decisions import (
    GENERATE_RESPONSE_INSTRUCTION,
    MultiSeatChoiceDecision,
    SeatChoiceDecision,
    SpeechDecision,
    YesNoDecision,
    extract_public_text,
    is_valid_public_speech,
    normalize_speech_decision,
)
from llm_werewolf.core.types import AgentProtocol, PlayerProtocol

if TYPE_CHECKING:
    pass


class WerewolfAdapterBridge:
    """Parses LLM responses and drives AgentProtocol / AgentScope agents."""

    # ------------------------------------------------------------------
    # Seat helpers (global numbering: player_N → seat N)
    # ------------------------------------------------------------------

    @staticmethod
    def get_player_seat(player: PlayerProtocol) -> int | None:
        """Return stable 1-based seat number for a player."""
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
        """Match a seat number to a player in the candidate list."""
        for player in candidates:
            if WerewolfAdapterBridge.get_player_seat(player) == seat:
                return player
        return None

    # ------------------------------------------------------------------
    # Parsing (text / structured → engine semantics)
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
        """Split raw model text into public speech and private thought."""
        private_blocks = re.findall(r"\{([^}]*)\}", response, flags=re.S)
        private_thought = "\n".join(b.strip() for b in private_blocks if b.strip()) or None
        decision = SpeechDecision(
            public_speech=extract_public_text(response),
            private_thought=private_thought,
        )
        return normalize_speech_decision(decision, raw_fallback=response)

    # ------------------------------------------------------------------
    # Prompt builders (engine → LLM)
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
        if structured:
            skip_hint = "；若不行动则 seat=0" if allow_skip else ""
            prompt_parts.extend([
                "",
                "请调用 generate_response，在 seat 字段填写目标的全局座位号"
                f"{skip_hint}。reason 可写私人理由。",
                GENERATE_RESPONSE_INSTRUCTION,
            ])
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
        structured: bool = False,
    ) -> str:
        parts = [context]
        if instruction:
            parts.extend(["", instruction])
        parts.extend(["", GamePrompts.SPEECH_PROMPT])
        if structured:
            parts.extend([
                "",
                "请调用 generate_response：public_speech 为完整中文发言（≥6 字，建议≥10 字），",
                "private_thought 为仅自己可见的推理。禁止把座位号写在 public_speech。",
                GENERATE_RESPONSE_INSTRUCTION,
            ])
        else:
            parts.extend([
                "",
                "格式提醒：本任务是「发言」，不是投票/选目标。",
                "[[...]] 内必须是完整中文句子（≥15 字），禁止只写 [[数字]]。",
                "私人推理写在 {...} 中，不要写在 [[]] 里。",
                "不要替尚未发言的玩家编造发言。",
            ])
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Agent invocation (generate_response → Msg.metadata; legacy text fallback)
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
    ) -> SpeechDecision:
        structured = agent_uses_structured_output(agent)
        prompt = WerewolfAdapterBridge.build_speech_prompt(
            context, instruction, structured=structured
        )
        legacy_prompt = WerewolfAdapterBridge.build_speech_prompt(
            context, instruction, structured=False
        )
        try:
            if structured:
                result = await invoke_structured(agent, prompt, SpeechDecision)
                if result is not None:
                    speech = coerce_speech(result)
                    if is_valid_public_speech(speech.public_speech):
                        return speech
                response = await agent.get_response(legacy_prompt)
                return WerewolfAdapterBridge.parse_speech(response)
            response = await agent.get_response(legacy_prompt)
            return WerewolfAdapterBridge.parse_speech(response)
        except Exception:
            pass
        return SpeechDecision(
            public_speech="（无公开发言）",
            private_thought=None,
        )
