"""Night phase logic for the game engine."""

import random
from typing import TYPE_CHECKING
from collections.abc import Callable

from llm_werewolf.adapter.message_router import MessageRouter
from llm_werewolf.adapter.visibility import VisibilityChannel
from llm_werewolf.core.decisions import SpeechDecision
from llm_werewolf.core.event_visibility import ROUNDTABLE_HUB_EVENT_TYPES
from llm_werewolf.core.types import Camp, EventType, GamePhase, PlayerProtocol
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.game_state import GameState
from llm_werewolf.core.prompts.actions import EngineContexts

if TYPE_CHECKING:
    from llm_werewolf.core.actions.base import Action


class NightPhaseMixin:
    """Mixin for handling night phase logic."""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    process_actions: Callable
    resolve_deaths: Callable
    build_player_observation: Callable
    build_shared_observation: Callable

    def _build_werewolf_discussion_context(self, werewolf: PlayerProtocol) -> str:
        """Static wolf context; in-round pack chat uses MsgHub memory."""
        if not self.game_state:
            return ""

        werewolves = [
            p for p in self.game_state.get_players_by_camp(Camp.WEREWOLF) if p.is_alive()
        ]
        possible_targets = [
            p for p in self.game_state.get_alive_players() if p.get_camp() != Camp.WEREWOLF
        ]
        werewolf_names = [w.name for w in werewolves]
        target_names = [p.name for p in possible_targets]

        shared = self.build_shared_observation(
            werewolves,
            additional_notes=EngineContexts.werewolf_coordination_note(
                werewolf_names, target_names
            ),
            include_visible_events=True,
            exclude_event_types=ROUNDTABLE_HUB_EVENT_TYPES,
        )
        return shared + "\n" + EngineContexts.werewolf_discussion(
            werewolf.name,
            self.game_state.round_number,
            werewolf_names,
            target_names,
            "",
        )

    def _log_werewolf_speech(
        self,
        speaker: PlayerProtocol,
        decision: SpeechDecision,
    ) -> None:
        if not self.game_state:
            return
        wolf_ids = MessageRouter.wolf_player_ids(self.game_state.get_alive_players())
        self._log_event(
            MessageRouter.event_type_for_channel(VisibilityChannel.WOLF_TEAM),
            self.locale.get(
                "werewolf_discussion", player=speaker.name, speech=decision.public_speech
            ),
            data={
                "player_id": speaker.player_id,
                "player_name": speaker.name,
                "speech": decision.public_speech,
                "role": "Werewolf",
            },
            visible_to=wolf_ids,
        )

    async def _run_werewolf_discussion(self) -> list[str]:
        """Werewolf pack discussion via Hub; only wolves hear (engine-routed)."""
        if not self.game_state:
            return []

        messages: list[str] = []
        werewolves = [
            p for p in self.game_state.get_players_by_camp(Camp.WEREWOLF) if p.is_alive()
        ]

        if len(werewolves) <= 1:
            return messages

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_wake"),
            data={"action": "werewolves_wake"},
        )

        possible_targets = [
            p for p in self.game_state.get_alive_players() if p.get_camp() != Camp.WEREWOLF
        ]
        if not possible_targets:
            return messages

        target_names = [p.name for p in possible_targets]
        interaction = self.game_state.require_phase_interaction()

        def on_speech(
            speaker: PlayerProtocol,
            decision: SpeechDecision,
            _routed: object,
        ) -> None:
            self._log_werewolf_speech(speaker, decision)
            messages.append(f"🐺 {speaker.name}: {decision.public_speech}")

        try:
            await interaction.run_roundtable(
                werewolves,
                channel=VisibilityChannel.WOLF_TEAM,
                context_builder=self._build_werewolf_discussion_context,
                instruction="",
                phase=GamePhase.NIGHT.value,
                round_number=self.game_state.round_number,
                audience=werewolves,
                opening_announcement=(
                    f"狼人请睁眼。可选刀口目标：{', '.join(target_names)}。"
                    "请与队友讨论今晚击杀目标。"
                ),
                on_speech=on_speech,
            )
        except Exception as exc:
            self._log_event(
                EventType.ERROR,
                self.locale.get("discussion_failed", player="*", error=str(exc)),
                data={"error": str(exc)},
            )

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_vote"),
            data={"action": "werewolves_vote"},
        )

        return messages

    def _resolve_werewolf_votes(self) -> list[str]:
        """Resolve werewolf voting to determine kill target."""
        if not self.game_state:
            return []

        messages: list[str] = []

        if not self.game_state.werewolf_votes:
            return messages

        vote_counts: dict[str, int] = {}
        for target_id in self.game_state.werewolf_votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        max_votes = max(vote_counts.values())
        candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

        if candidates:
            selected_target_id = random.choice(candidates)  # noqa: S311
            self.game_state.werewolf_target = selected_target_id

            target = self.game_state.get_player(selected_target_id)
            if target:
                self._log_event(
                    EventType.WEREWOLF_KILLED,
                    self.locale.get("werewolf_target", target=target.name),
                    data={"target_id": selected_target_id, "target_name": target.name},
                )

        return messages

    async def run_night_phase(self) -> list[str]:
        """Execute the night phase where roles perform actions."""
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        messages: list[str] = []
        self.game_state.set_phase(GamePhase.NIGHT)

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_night_falls"),
            data={"action": "night_falls"},
        )

        self._log_event(
            EventType.PHASE_CHANGED,
            self.locale.get("night_begins", round_number=self.game_state.round_number),
            data={"phase": "night", "round": self.game_state.round_number},
        )

        messages.append("")

        discussion_messages = await self._run_werewolf_discussion()
        messages.extend(discussion_messages)

        players_with_night_actions = self.game_state.get_players_with_night_actions()

        for player in players_with_night_actions:
            role_name = player.get_role_name()
            self._log_event(
                EventType.ROLE_ACTING,
                self.locale.get("role_acting", role=role_name, player=player.name),
                data={"player_id": player.player_id, "role": role_name},
            )

        action_results = []
        for player in players_with_night_actions:
            try:
                result = await player.role.get_night_actions(self.game_state)
                action_results.append(result)
            except Exception as e:
                action_results.append(e)

        night_actions: list[Action] = []
        for player, result in zip(players_with_night_actions, action_results, strict=False):
            if isinstance(result, Exception):
                self._log_event(
                    EventType.ERROR,
                    self.locale.get(
                        "night_action_failed",
                        player=player.name,
                        role=player.get_role_name(),
                        error=str(result),
                    ),
                    data={
                        "player_id": player.player_id,
                        "error": str(result),
                        "error_type": type(result).__name__,
                    },
                )
                continue
            if result:
                night_actions.extend(result)

        action_messages = self.process_actions(night_actions)
        messages.extend(action_messages)

        werewolf_vote_messages = self._resolve_werewolf_votes()
        messages.extend(werewolf_vote_messages)

        death_messages = await self.resolve_deaths()
        messages.extend(death_messages)

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_sleep"),
            data={"action": "werewolves_sleep"},
        )

        return messages
