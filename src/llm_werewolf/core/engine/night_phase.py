"""Night phase logic for the game engine."""

import random
import asyncio
from typing import TYPE_CHECKING
from collections.abc import Callable

from llm_werewolf.core.types import Camp, EventType, GamePhase
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
    werewolf_discussion_history: list[str]
    _get_werewolf_discussion_context: Callable[[], str]
    build_player_observation: Callable
    build_shared_observation: Callable

    async def _run_werewolf_discussion(self) -> list[str]:
        """Run werewolf discussion phase where werewolves discuss their target.

        Returns:
            list[str]: Messages from the discussion.
        """
        if not self.game_state:
            return []

        messages: list[str] = []
        werewolves = [
            p for p in self.game_state.get_players_by_camp(Camp.WEREWOLF) if p.is_alive()
        ]

        if len(werewolves) <= 1:
            # If only one werewolf, skip discussion
            return messages

        # Narrator: Werewolves wake up
        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_wake"),
            data={"action": "werewolves_wake"},
        )

        # Get possible targets
        possible_targets = [
            p for p in self.game_state.get_alive_players() if p.get_camp() != Camp.WEREWOLF
        ]

        if not possible_targets:
            return messages

        target_names = [p.name for p in possible_targets]
        werewolf_names = [w.name for w in werewolves]

        # Each werewolf discusses
        for werewolf in werewolves:
            if werewolf.agent:
                shared_observation = self.build_shared_observation(
                    werewolves,
                    additional_notes=EngineContexts.werewolf_coordination_note(
                        werewolf_names, target_names
                    ),
                    include_visible_events=True,
                )
                werewolf_history = self._get_werewolf_discussion_context()
                context = shared_observation + "\n" + EngineContexts.werewolf_discussion(
                    werewolf.name,
                    self.game_state.round_number,
                    werewolf_names,
                    target_names,
                    werewolf_history,
                )

                try:
                    speech = await werewolf.agent.get_response(context)

                    self._log_event(
                        EventType.PLAYER_DISCUSSION,
                        self.locale.get(
                            "werewolf_discussion", player=werewolf.name, speech=speech
                        ),
                        data={
                            "player_id": werewolf.player_id,
                            "player_name": werewolf.name,
                            "speech": speech,
                            "role": "Werewolf",
                        },
                    )

                    messages.append(f"🐺 {werewolf.name}: {speech}")

                    # Add to global werewolf discussion history
                    self.werewolf_discussion_history.append(f"{werewolf.name}: {speech}")

                    # Record werewolf's own speech in decision history
                    # This is safe: only records what they said, not sensitive context
                    werewolf.agent.add_decision(
                        f"Round {self.game_state.round_number} (Werewolf discussion): You said: {speech}"
                    )
                except Exception as e:
                    self._log_event(
                        EventType.ERROR,
                        self.locale.get("discussion_failed", player=werewolf.name, error=str(e)),
                        data={"player_id": werewolf.player_id, "error": str(e)},
                    )

        # Narrator: Time to vote
        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_vote"),
            data={"action": "werewolves_vote"},
        )

        return messages

    def _resolve_werewolf_votes(self) -> list[str]:
        """Resolve werewolf voting to determine kill target.

        Returns:
            list[str]: Messages describing the voting result.
        """
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
        """Execute the night phase where roles perform actions.

        Returns:
            list[str]: Messages describing night actions.
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        messages = []
        self.game_state.set_phase(GamePhase.NIGHT)

        # Narrator: Night falls
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

        # Run werewolf discussion phase (if multiple werewolves exist)
        discussion_messages = await self._run_werewolf_discussion()
        messages.extend(discussion_messages)

        # Get players with night actions (non-werewolf roles)
        players_with_night_actions = self.game_state.get_players_with_night_actions()

        # Log that roles are acting, then gather all night actions concurrently
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
        for player, result in zip(players_with_night_actions, action_results):
            if isinstance(result, Exception):
                self._log_event(
                    EventType.ERROR,
                    self.locale.get("night_action_failed", player=player.name, role=player.get_role_name(), error=str(result)),
                    data={"player_id": player.player_id, "error": str(result), "error_type": type(result).__name__},
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

        # Narrator: Werewolves sleep (end of night)
        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_sleep"),
            data={"action": "werewolves_sleep"},
        )

        return messages
