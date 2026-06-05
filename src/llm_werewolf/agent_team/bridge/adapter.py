"""LLM 输出、AgentScope Agent 与游戏引擎之间的统一适配层。

所有基于座位的决策、结构化输出解析与 Agent 调用应经本模块
（通过 InformationHub / PhaseInteraction）完成。
后续扩展（如信念矩阵）可在此添加决策模型并接入下方 request_* 方法。
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from llm_werewolf.game_runtime.support.seat import get_player_seat, resolve_player_by_seat

from llm_werewolf.strategy.contracts.decisions import (
    YesNoDecision,
    SpeechDecision,
    SeatChoiceDecision,
    WitchNightDecision,
    VoteIntentionDecision,
    MindStateDecision,
    MultiSeatChoiceDecision,
    is_valid_public_speech,
    validate_mind_state_decision,
    validate_seat_choice_reason,
)
from llm_werewolf.strategy.belief.state import MindStateResult
from llm_werewolf.strategy.contracts.phase_outputs import (
    ActionPhase,
    RoundtablePhase,
)
from llm_werewolf.strategy.voting.intention import VoteIntentionEntry, VoteIntentionAnchor
from llm_werewolf.game_runtime.prompts.decision_fallback import select_target_fallback
from llm_werewolf.agent_team.invocation.structured_invoke import (
    coerce_speech,
    invoke_structured,
    agent_uses_structured_output,
)
from llm_werewolf.agent_team.bridge.parsing import (
    parse_speech as _parse_speech,
    parse_yes_no as _parse_yes_no,
    parse_target_selection as _parse_target_selection,
    parse_multi_target_selection as _parse_multi_target_selection,
)
from llm_werewolf.agent_team.bridge.prompts import (
    build_speech_prompt as _build_speech_prompt,
    build_yes_no_prompt as _build_yes_no_prompt,
    build_mind_state_prompt as _build_mind_state_prompt,
    build_witch_night_prompt as _build_witch_night_prompt,
    build_multi_target_prompt as _build_multi_target_prompt,
    build_vote_intention_prompt as _build_vote_intention_prompt,
    build_target_selection_prompt as _build_target_selection_prompt,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

    from llm_werewolf.game_runtime.types import AgentProtocol, PlayerProtocol


logger = logging.getLogger(__name__)


class WerewolfAdapterBridge:
    """解析 LLM 回复并驱动 AgentProtocol / AgentScope Agent。"""

    # ------------------------------------------------------------------
    # 座位辅助（全局编号：player_N → 座位 N）
    # ------------------------------------------------------------------

    @staticmethod
    def get_player_seat(player: PlayerProtocol) -> int | None:
        """返回玩家稳定的 1 基座位号。"""
        return get_player_seat(player)

    @staticmethod
    def resolve_player_by_seat(
        seat: int, candidates: list[PlayerProtocol]
    ) -> PlayerProtocol | None:
        """在候选列表中按座位号匹配玩家。"""
        return resolve_player_by_seat(seat, candidates)

    # ------------------------------------------------------------------
    # 解析（文本 / 结构化 → 引擎语义）
    # ------------------------------------------------------------------

    @staticmethod
    def parse_target_selection(
        response: str, possible_targets: list[PlayerProtocol], allow_skip: bool = False
    ) -> PlayerProtocol | None:
        return _parse_target_selection(response, possible_targets, allow_skip)

    @staticmethod
    def parse_yes_no(response: str) -> bool:
        return _parse_yes_no(response)

    @staticmethod
    def parse_multi_target_selection(
        response: str, possible_targets: list[PlayerProtocol], num_targets: int
    ) -> list[PlayerProtocol] | None:
        return _parse_multi_target_selection(response, possible_targets, num_targets)

    @staticmethod
    def parse_speech(response: str) -> SpeechDecision:
        """将模型原始文本拆分为公开发言与私人推理。"""
        return _parse_speech(response)

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
        require_reason: bool = False,
    ) -> str:
        return _build_target_selection_prompt(
            role_name,
            action_description,
            possible_targets,
            allow_skip,
            additional_context,
            round_number,
            phase,
            structured=structured,
            action_phase=action_phase,
            require_reason=require_reason,
        )

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
        return _build_yes_no_prompt(
            role_name,
            question,
            context,
            round_number,
            phase,
            structured=structured,
        )

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
        return _build_multi_target_prompt(
            role_name,
            action_description,
            possible_targets,
            num_targets,
            additional_context,
            round_number,
            phase,
            structured=structured,
        )

    @staticmethod
    def build_speech_prompt(
        context: str,
        instruction: str = "",
        *,
        structured: bool = True,
        roundtable_phase: RoundtablePhase | None = None,
    ) -> str:
        return _build_speech_prompt(
            context,
            instruction,
            structured=structured,
            roundtable_phase=roundtable_phase,
        )

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
        fallback_reason: str | None = None,
    ) -> None:
        if target is None:
            return

        metadata: dict[str, Any] = {
            "decision_seat": WerewolfAdapterBridge.get_player_seat(target),
            "resolved_target_id": target.player_id,
            "resolved_target_name": target.name,
            "fallback": fallback,
        }
        if fallback_reason:
            metadata["fallback_reason"] = fallback_reason
        if response is not None:
            metadata["raw_response"] = response
        if decision is not None:
            metadata["structured_decision"] = decision.model_dump(mode="json")

        object.__setattr__(agent, "_last_decision_metadata", metadata)

    @staticmethod
    def _random_fallback_target(
        agent: AgentProtocol,
        possible_targets: list[PlayerProtocol],
        *,
        reason: str,
    ) -> PlayerProtocol:
        fallback = select_target_fallback(
            possible_targets, allow_random=True, reason=reason
        )
        if fallback.target is None:
            msg = "random fallback requested without possible targets"
            raise ValueError(msg)
        WerewolfAdapterBridge._store_decision_metadata(
            agent,
            fallback.target,
            fallback=True,
            fallback_reason=fallback.reason,
        )
        return fallback.target

    @staticmethod
    def _clear_decision_metadata(agent: AgentProtocol) -> None:
        object.__setattr__(agent, "_last_decision_metadata", None)

    @staticmethod
    def _with_formal_vote_reason(
        decision: SeatChoiceDecision, target: PlayerProtocol | None
    ) -> SeatChoiceDecision:
        if not validate_seat_choice_reason(decision):
            return decision

        if decision.seat == 0:
            reason = "模型未提供正式投票理由，保留其弃票选择。"
        else:
            target_name = target.name if target is not None else f"{decision.seat}号"
            reason = f"模型未提供正式投票理由，保留其投票目标：{target_name}。"
        return decision.model_copy(update={"reason": reason})

    @staticmethod
    def build_witch_night_prompt(
        role_name: str,
        *,
        can_see_victim: bool,
        can_save: bool,
        victim_line: str,
        poison_targets: list[PlayerProtocol],
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
        structured: bool = False,
    ) -> str:
        return _build_witch_night_prompt(
            role_name,
            can_see_victim=can_see_victim,
            can_save=can_save,
            victim_line=victim_line,
            poison_targets=poison_targets,
            additional_context=additional_context,
            round_number=round_number,
            phase=phase,
            structured=structured,
        )

    @staticmethod
    async def request_witch_night_choice(
        agent: AgentProtocol,
        role_name: str,
        *,
        can_see_victim: bool,
        can_save: bool,
        victim_line: str,
        poison_targets: list[PlayerProtocol],
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> WitchNightDecision:
        """返回女巫夜间决策；失败时默认为 none。"""
        WerewolfAdapterBridge._clear_decision_metadata(agent)
        structured = agent_uses_structured_output(agent) or callable(
            getattr(agent, "get_structured_response", None)
        )
        prompt = WerewolfAdapterBridge.build_witch_night_prompt(
            role_name,
            can_see_victim=can_see_victim,
            can_save=can_save,
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
                    if result.action == "save" and not can_save:
                        WerewolfAdapterBridge._store_decision_metadata(
                            agent, None, decision=default
                        )
                        return default
                    WerewolfAdapterBridge._store_decision_metadata(agent, None, decision=result)
                    return result
            response = await agent.get_response(prompt)
            lowered = response.lower()
            if "save" in lowered or "救" in response:
                if not can_save:
                    return default
                return WitchNightDecision(action="save", seat=0, reason=response[:200])
            if "poison" in lowered or "毒" in response:
                seat_match = re.search(r"\[\[\s*(\d+)\s*\]\]", response)
                if not seat_match:
                    return default
                seat = int(seat_match.group(1))
                if seat <= 0:
                    return default
                poison_target = WerewolfAdapterBridge.resolve_player_by_seat(seat, poison_targets)
                if poison_target is None:
                    return default
                return WitchNightDecision(action="poison", seat=seat, reason=response[:200])
        except Exception:
            logger.warning("request_witch_night_choice failed, using default", exc_info=True)
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
        return _build_vote_intention_prompt(
            role_name,
            possible_targets,
            additional_context,
            anchor=anchor,
            last_speaker_name=last_speaker_name,
            round_number=round_number,
            phase=phase,
            structured=structured,
        )

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
        structured = agent_uses_structured_output(agent) or callable(
            getattr(agent, "get_structured_response", None)
        )
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
            if (
                safe_seat > 0
                and WerewolfAdapterBridge.resolve_player_by_seat(safe_seat, possible_targets)
                is None
            ):
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
            logger.warning(
                "request_vote_intention failed agent=%s, using seat=0 fallback",
                getattr(agent, "name", "?"),
                exc_info=True,
            )
            return _entry_from_seat(0, msg)

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
    def _mind_state_from_decision(decision: MindStateDecision) -> MindStateResult:
        return MindStateResult(
            vote_seat=decision.seat,
            vote_reason=decision.reason,
            first_order=list(decision.first_order),
            second_order=list(decision.second_order),
            wolf_camp_delta=decision.wolf_camp_delta,
        )

    @staticmethod
    def build_mind_state_prompt(
        role_name: str,
        possible_targets: list[PlayerProtocol],
        additional_context: str,
        *,
        anchor: VoteIntentionAnchor,
        last_speaker_name: str | None = None,
        round_number: int | None = None,
        phase: str | None = None,
        structured: bool = False,
        belief_summary: str = "",
        wolf_camp_context: str = "",
    ) -> str:
        return _build_mind_state_prompt(
            role_name,
            possible_targets,
            additional_context,
            anchor=anchor,
            last_speaker_name=last_speaker_name,
            round_number=round_number,
            phase=phase,
            structured=structured,
            belief_summary=belief_summary,
            wolf_camp_context=wolf_camp_context,
        )

    @staticmethod
    async def request_mind_state(
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
        belief_summary: str = "",
        wolf_camp_context: str = "",
    ) -> tuple[VoteIntentionEntry, MindStateResult]:
        """采集投票意向与信念矩阵（单次 LLM 结构化调用）。"""
        structured = agent_uses_structured_output(agent) or callable(
            getattr(agent, "get_structured_response", None)
        )
        prompt = WerewolfAdapterBridge.build_mind_state_prompt(
            role_name,
            possible_targets,
            additional_context,
            anchor=anchor,
            last_speaker_name=last_speaker_name,
            round_number=round_number,
            phase=phase,
            structured=structured,
            belief_summary=belief_summary,
            wolf_camp_context=wolf_camp_context,
        )

        def _entry_from_mind(mind: MindStateResult) -> VoteIntentionEntry:
            safe_seat = max(0, int(mind.vote_seat))
            if (
                safe_seat > 0
                and WerewolfAdapterBridge.resolve_player_by_seat(safe_seat, possible_targets)
                is None
            ):
                safe_seat = 0
            return WerewolfAdapterBridge.build_vote_intention_entry(
                actor, safe_seat, possible_targets, mind.vote_reason
            )

        def _finalize_mind(mind: MindStateResult) -> tuple[VoteIntentionEntry, MindStateResult]:
            belief_state = getattr(agent, "belief_state", None)
            previous_vote_seat = (
                belief_state.last_vote_seat
                if belief_state is not None and hasattr(belief_state, "last_vote_seat")
                else None
            )
            decision = MindStateDecision(
                seat=mind.vote_seat,
                reason=mind.vote_reason,
                first_order=mind.first_order,
                second_order=mind.second_order,
                wolf_camp_delta=mind.wolf_camp_delta,
            )
            errors = validate_mind_state_decision(
                decision,
                previous_vote_seat=previous_vote_seat,
            )
            if errors:
                msg = "; ".join(errors)
                raise ValueError(msg)
            return _entry_from_mind(mind), mind

        last_error: str | None = None
        if structured:
            try:
                result = await invoke_structured(agent, prompt, MindStateDecision)
                if isinstance(result, MindStateDecision):
                    mind = WerewolfAdapterBridge._mind_state_from_decision(result)
                    return _finalize_mind(mind)
            except Exception as exc:
                last_error = str(exc)

        try:
            response = await agent.get_response(prompt)
        except Exception as exc:
            msg = f"mind_state LLM failed: {last_error or exc}"
            raise RuntimeError(msg) from exc

        from llm_werewolf.agent_team.invocation.structured_invoke import parse_structured_from_text

        parsed = parse_structured_from_text(response, MindStateDecision)
        if parsed is not None:
            if not (parsed.reason and parsed.reason.strip()):
                stripped = (response or "").strip()
                parsed = parsed.model_copy(
                    update={
                        "reason": stripped[:500]
                        if stripped
                        else (f"fallback seat={max(0, int(parsed.seat))}")
                    }
                )
            mind = WerewolfAdapterBridge._mind_state_from_decision(parsed)
            return _finalize_mind(mind)

        def _fallback_mind_from_seat(seat: int, reason_text: str) -> tuple[VoteIntentionEntry, MindStateResult]:
            safe_seat = max(0, int(seat))
            if (
                safe_seat > 0
                and WerewolfAdapterBridge.resolve_player_by_seat(safe_seat, possible_targets)
                is None
            ):
                safe_seat = 0
            fallback_reason = (reason_text or "").strip()[:500]
            if not fallback_reason:
                if safe_seat > 0:
                    fallback_reason = f"fallback seat={safe_seat}"
                else:
                    fallback_reason = "fallback seat=0"
            mind = MindStateResult(
                vote_seat=safe_seat,
                vote_reason=fallback_reason,
                first_order=[],
                second_order=[],
            )
            return _entry_from_mind(mind), mind

        target = WerewolfAdapterBridge.parse_target_selection(
            response, possible_targets, allow_skip=True
        )
        if target is not None:
            seat = WerewolfAdapterBridge.get_player_seat(target) or 0
            return _fallback_mind_from_seat(seat, response)

        numbers = re.findall(r"\[\[\s*(\d+)\s*\]\]", response)
        if numbers:
            seat = int(numbers[0])
            return _fallback_mind_from_seat(seat, response)
        loose = re.findall(r"\d+", response.strip())
        if loose:
            seat = int(loose[0])
            return _fallback_mind_from_seat(seat, response)
        mind = MindStateResult(
            vote_seat=0,
            vote_reason=(response[:500].strip() if response[:500].strip() else "fallback seat=0"),
            first_order=[],
            second_order=[],
        )
        return _finalize_mind(mind)

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

        structured = agent_uses_structured_output(agent) or callable(
            getattr(agent, "get_structured_response", None)
        )
        require_reason = action_phase == ActionPhase.DAY_VOTE
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
            require_reason=require_reason,
        )

        try:
            if structured:
                result = await invoke_structured(agent, prompt, SeatChoiceDecision)
                if isinstance(result, SeatChoiceDecision):
                    if allow_skip and result.seat == 0:
                        if require_reason:
                            result = WerewolfAdapterBridge._with_formal_vote_reason(
                                result, None
                            )
                        WerewolfAdapterBridge._store_decision_metadata(
                            agent, None, decision=result
                        )
                        return None
                    target = WerewolfAdapterBridge.resolve_player_by_seat(
                        result.seat, possible_targets
                    )
                    if target is not None:
                        if require_reason:
                            result = WerewolfAdapterBridge._with_formal_vote_reason(
                                result, target
                            )
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
                return WerewolfAdapterBridge._random_fallback_target(
                    agent, possible_targets, reason="parse_failed"
                )
        except Exception as exc:
            logger.warning(
                "request_seat_choice failed agent=%s, using random fallback=%s",
                getattr(agent, "name", "?"),
                fallback_random,
                exc_info=True,
            )
            if fallback_random:
                return WerewolfAdapterBridge._random_fallback_target(
                    agent, possible_targets, reason=type(exc).__name__
                )

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
        structured = agent_uses_structured_output(agent) or callable(
            getattr(agent, "get_structured_response", None)
        )
        prompt = WerewolfAdapterBridge.build_yes_no_prompt(
            role_name, question, context, round_number, phase, structured=structured
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
        except Exception as exc:
            logger.warning(
                "request_yes_no failed agent=%s, defaulting to False",
                getattr(agent, "name", "?"),
                exc_info=True,
            )
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

        structured = agent_uses_structured_output(agent) or callable(
            getattr(agent, "get_structured_response", None)
        )
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
                result = await invoke_structured(agent, prompt, MultiSeatChoiceDecision)
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
            logger.warning("request_multi_target failed agent=%s", getattr(agent, "name", "?"), exc_info=True)
        return None

    @staticmethod
    async def request_speech(
        agent: AgentProtocol,
        context: str,
        instruction: str = "",
        *,
        schema_retries: int = 1,
        roundtable_phase: RoundtablePhase | None = None,
    ) -> SpeechDecision:
        structured = agent_uses_structured_output(agent) or callable(
            getattr(agent, "get_structured_response", None)
        )
        prompt = WerewolfAdapterBridge.build_speech_prompt(
            context, instruction, structured=structured, roundtable_phase=roundtable_phase
        )
        try:
            if structured:
                for _ in range(schema_retries):
                    result = await invoke_structured(agent, prompt, SpeechDecision, retries=1)
                    if result is not None:
                        speech = coerce_speech(result)
                        if is_valid_public_speech(speech.public_speech):
                            return speech
                    break
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
            logger.warning("request_speech failed agent=%s, using fallback", getattr(agent, "name", "?"), exc_info=True)
        fallback_getter = getattr(agent, "_generate_fallback_response", None)
        if callable(fallback_getter):
            raw = fallback_getter(prompt, "speech_fallback")
            parsed = WerewolfAdapterBridge.parse_speech(raw)
            if is_valid_public_speech(parsed.public_speech):
                return parsed
        # 最终兜底：返回一条合法的公开发言（≥15字）
        return SpeechDecision(
            public_speech="目前场上信息还不够，我需要多听几轮发言再做判断。先观察大家的站队和投票倾向，重点关注发言前后矛盾的人。",
            private_thought=None,
        )
