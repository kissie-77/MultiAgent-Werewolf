"""对局内所有智能体交互的统一入口（InformationHub 门面）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
import asyncio

from llm_werewolf.game_runtime.events.visibility import VisibilityChannel

if TYPE_CHECKING:
    from collections.abc import Callable

    from llm_werewolf.game_runtime.types import AgentProtocol, PlayerProtocol
    from llm_werewolf.strategy.decisions import SpeechDecision, WitchNightDecision
    from llm_werewolf.strategy.phase_outputs import ActionPhase
    from llm_werewolf.strategy.vote_intention import (
        VoteIntentionTracker,
        SpeechVoteIntentionRecord,
    )
    from llm_werewolf.game_runtime.events.visibility import RoutedMessage


class PhaseInteractionHub(Protocol):
    """Runtime-facing contract implemented by the agent communication hub."""

    def set_context_provider(
        self,
        *,
        build_observation: Callable[[PlayerProtocol], str],
        get_alive_players: Callable[[], list[PlayerProtocol]],
    ) -> None: ...

    async def request_private_seat_choice(
        self,
        actor: PlayerProtocol,
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
    ) -> PlayerProtocol | None: ...

    async def request_private_witch_night(
        self,
        actor: PlayerProtocol,
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
    ) -> WitchNightDecision: ...

    async def request_private_yes_no(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        question: str,
        context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> bool: ...

    async def request_private_multi_target(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> list[PlayerProtocol] | None: ...

    async def collect_speech(
        self,
        speaker: PlayerProtocol,
        context: str,
        *,
        channel: VisibilityChannel,
        instruction: str = "",
        phase: str = "",
        round_number: int = 0,
        audience: list[PlayerProtocol] | None = None,
    ) -> SpeechDecision: ...

    async def announce(
        self,
        content: str,
        *,
        channel: VisibilityChannel = VisibilityChannel.PUBLIC,
        audience: list[PlayerProtocol] | None = None,
        phase: str = "",
        round_number: int = 0,
    ) -> None: ...

    async def run_roundtable(
        self,
        speakers: list[PlayerProtocol],
        *,
        channel: VisibilityChannel,
        context_builder: Callable[[PlayerProtocol], str],
        instruction: str,
        phase: str,
        round_number: int,
        audience: list[PlayerProtocol] | None = None,
        opening_announcement: str = "",
        on_speech: Callable[[PlayerProtocol, SpeechDecision, RoutedMessage | None], None]
        | None = None,
        vote_intention_tracker: VoteIntentionTracker | None = None,
        on_vote_intention_record: Callable[[SpeechVoteIntentionRecord], None] | None = None,
    ) -> list[RoutedMessage]: ...


class PhaseInteraction:
    """面向引擎与角色的 LLM 决策 API。须显式注入 hub。"""

    def __init__(self, hub: PhaseInteractionHub) -> None:
        self._hub = hub
        self._night_timeout: float | None = None
        self._day_timeout: float | None = None
        self._vote_timeout: float | None = None

    def configure_timeouts(
        self,
        *,
        night_timeout: int | None = None,
        day_timeout: int | None = None,
        vote_timeout: int | None = None,
    ) -> None:
        """从 GameConfig 注入各阶段 LLM 调用超时（秒）。"""
        self._night_timeout = float(night_timeout) if night_timeout else None
        self._day_timeout = float(day_timeout) if day_timeout else None
        self._vote_timeout = float(vote_timeout) if vote_timeout else None

    def _timeout_for_phase(self, phase: str | None) -> float | None:
        if not phase:
            return self._night_timeout
        normalized = phase.strip().lower()
        if normalized in {"voting", "sheriffvoting", "day_voting"}:
            return self._vote_timeout
        if normalized in {
            "day",
            "sheriff",
            "discussion",
            "day_discussion",
            "sheriff_election",
        }:
            return self._day_timeout
        return self._night_timeout

    async def _await_with_timeout(self, coro, phase: str | None):
        timeout = self._timeout_for_phase(phase)
        if timeout is None or timeout <= 0:
            return await coro
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except TimeoutError as exc:
            label = phase or "unknown"
            msg = f"{label} phase timed out after {int(timeout)}s"
            raise TimeoutError(msg) from exc

    @property
    def hub(self) -> PhaseInteractionHub:
        return self._hub

    async def request_seat_choice(
        self,
        actor: PlayerProtocol,
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
        return await self._await_with_timeout(
            self._hub.request_private_seat_choice(
                actor,
                agent,
                role_name,
                action_description,
                possible_targets,
                allow_skip,
                additional_context,
                fallback_random,
                round_number,
                phase,
                action_phase,
            ),
            phase,
        )

    async def request_witch_night_choice(
        self,
        actor: PlayerProtocol,
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
        return await self._await_with_timeout(
            self._hub.request_private_witch_night(
                actor,
                agent,
                role_name,
                can_see_victim=can_see_victim,
                can_save=can_save,
                victim_line=victim_line,
                poison_targets=poison_targets,
                additional_context=additional_context,
                round_number=round_number,
                phase=phase,
            ),
            phase,
        )

    async def request_yes_no(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        question: str,
        context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> bool:
        return await self._await_with_timeout(
            self._hub.request_private_yes_no(
                actor, agent, role_name, question, context, round_number, phase
            ),
            phase,
        )

    async def request_multi_targets(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> list[PlayerProtocol] | None:
        return await self._await_with_timeout(
            self._hub.request_private_multi_target(
                actor,
                agent,
                role_name,
                action_description,
                possible_targets,
                num_targets,
                additional_context,
                round_number,
                phase,
            ),
            phase,
        )

    async def request_speech(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        context: str,
        instruction: str = "",
        *,
        channel: VisibilityChannel = VisibilityChannel.PUBLIC,
        phase: str = "",
        round_number: int = 0,
        audience: list[PlayerProtocol] | None = None,
    ) -> SpeechDecision:
        return await self._await_with_timeout(
            self._hub.collect_speech(
                actor,
                context,
                channel=channel,
                instruction=instruction,
                phase=phase,
                round_number=round_number,
                audience=audience,
            ),
            phase,
        )

    async def announce(
        self,
        content: str,
        *,
        channel: VisibilityChannel = VisibilityChannel.PUBLIC,
        audience: list[PlayerProtocol] | None = None,
        phase: str = "",
        round_number: int = 0,
    ) -> None:
        await self._hub.announce(
            content, channel=channel, audience=audience, phase=phase, round_number=round_number
        )

    async def run_roundtable(
        self,
        speakers: list[PlayerProtocol],
        *,
        channel: VisibilityChannel,
        context_builder: Callable[[PlayerProtocol], str],
        instruction: str,
        phase: str,
        round_number: int,
        audience: list[PlayerProtocol] | None = None,
        opening_announcement: str = "",
        on_speech: Callable[[PlayerProtocol, SpeechDecision, RoutedMessage | None], None]
        | None = None,
        vote_intention_tracker: VoteIntentionTracker | None = None,
        on_vote_intention_record: Callable[[SpeechVoteIntentionRecord], None] | None = None,
    ) -> list:
        # Roundtable may include many sequential LLM steps; per-step timeouts are
        # enforced inside InformationHub, not as one budget for the whole discussion.
        return await self._hub.run_roundtable(
            speakers,
            channel=channel,
            context_builder=context_builder,
            instruction=instruction,
            phase=phase,
            round_number=round_number,
            audience=audience,
            opening_announcement=opening_announcement,
            on_speech=on_speech,
            vote_intention_tracker=vote_intention_tracker,
            on_vote_intention_record=on_vote_intention_record,
        )
