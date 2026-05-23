"""对局内所有智能体交互的统一入口（InformationHub 门面）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from llm_werewolf.adapter.information_hub import InformationHub
from llm_werewolf.adapter.visibility import VisibilityChannel
from llm_werewolf.core.decisions import SpeechDecision, WitchNightDecision
from llm_werewolf.core.vote_intention import SpeechVoteIntentionRecord, VoteIntentionTracker
from llm_werewolf.core.phase_outputs import ActionPhase
from llm_werewolf.core.types import AgentProtocol, PlayerProtocol

if TYPE_CHECKING:
    from llm_werewolf.adapter.visibility import RoutedMessage


class PhaseInteraction:
    """面向引擎与角色的 LLM 决策 API。须显式注入 hub。"""

    def __init__(self, hub: InformationHub) -> None:
        self._hub = hub

    @property
    def hub(self) -> InformationHub:
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
        return await self._hub.request_private_seat_choice(
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
        )

    async def request_witch_night_choice(
        self,
        actor: PlayerProtocol,
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
        return await self._hub.request_private_witch_night(
            actor,
            agent,
            role_name,
            can_see_victim=can_see_victim,
            victim_line=victim_line,
            poison_targets=poison_targets,
            additional_context=additional_context,
            round_number=round_number,
            phase=phase,
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
        return await self._hub.request_private_yes_no(
            actor, agent, role_name, question, context, round_number, phase
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
        return await self._hub.request_private_multi_target(
            actor,
            agent,
            role_name,
            action_description,
            possible_targets,
            num_targets,
            additional_context,
            round_number,
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
        return await self._hub.collect_speech(
            actor,
            context,
            channel=channel,
            instruction=instruction,
            phase=phase,
            round_number=round_number,
            audience=audience,
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
            content,
            channel=channel,
            audience=audience,
            phase=phase,
            round_number=round_number,
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
        on_speech: Callable[
            [PlayerProtocol, SpeechDecision, RoutedMessage | None], None
        ]
        | None = None,
        vote_intention_tracker: VoteIntentionTracker | None = None,
        on_vote_intention_record: Callable[[SpeechVoteIntentionRecord], None]
        | None = None,
    ) -> list:
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
