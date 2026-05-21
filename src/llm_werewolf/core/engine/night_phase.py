"""Night phase logic for the game engine."""

import random
import asyncio
from typing import TYPE_CHECKING
from collections.abc import Callable

from llm_werewolf.core.types import Camp, EventType, GamePhase
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.game_state import GameState
from llm_werewolf.adapter.visibility import VisibilityChannel
from llm_werewolf.core.night_scheduler import NightSkillScheduler

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
    information_hub: object

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

        wolf_ids = [w.player_id for w in werewolves]

        def _wolf_context(speaker) -> str:
            shared_observation = self.build_shared_observation(
                werewolves,
                additional_notes=[
                    f"You are coordinating with these werewolves: {', '.join(werewolf_names)}.",
                    f"Available targets: {', '.join(target_names)}.",
                ],
                include_visible_events=True,
            )
            context_parts = [
                shared_observation,
                f"You are {speaker.name}, a Werewolf.",
                f"Current: Round {self.game_state.round_number} - Night Phase",
                f"You are working with these werewolves: {', '.join(werewolf_names)}.",
                f"Available targets: {', '.join(target_names)}.",
            ]
            return "\n".join(context_parts)

        def _on_wolf_speech(speaker, decision, _routed) -> None:
            speech = decision.public_speech.strip()
            self._log_event(
                EventType.PLAYER_DISCUSSION,
                self.locale.get("werewolf_discussion", player=speaker.name, speech=speech),
                data={
                    "player_id": speaker.player_id,
                    "player_name": speaker.name,
                    "speech": speech,
                    "private_thought": decision.private_thought,
                    "role": "Werewolf",
                },
            )
            messages.append(f"🐺 {speaker.name}: {speech}")

        try:
            await self.information_hub.run_roundtable(
                werewolves,
                channel=VisibilityChannel.WOLF_TEAM,
                audience=werewolves,
                context_builder=_wolf_context,
                instruction=(
                    "Discuss with your fellow werewolves who should be eliminated tonight. "
                    "Share your thoughts (1-2 sentences)."
                ),
                phase="night",
                round_number=self.game_state.round_number,
                on_speech=_on_wolf_speech,
            )
        except Exception as e:
            self._log_event(
                EventType.ERROR,
                self.locale.get("discussion_failed", player="werewolves", error=str(e)),
                data={"error": str(e), "visibility": "wolf_team"},
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
                werewolf_votes = []
                for voter_id, target_id in self.game_state.werewolf_votes.items():
                    voter = self.game_state.get_player(voter_id)
                    voted_target = self.game_state.get_player(target_id)
                    werewolf_votes.append(
                        {
                            "voter_id": voter_id,
                            "voter_name": voter.name if voter else voter_id,
                            "target_id": target_id,
                            "target_name": voted_target.name if voted_target else target_id,
                        }
                    )
                self._log_event(
                    EventType.WEREWOLF_KILLED,
                    self.locale.get("werewolf_target", target=target.name),
                    data={
                        "target_id": selected_target_id,
                        "target_name": target.name,
                    },
                )
                self._log_event(
                    EventType.MESSAGE,
                    self.locale.get("werewolf_vote_tally", target=target.name),
                    data={
                        "action": "werewolf_vote_tally",
                        "target_id": selected_target_id,
                        "werewolf_votes": werewolf_votes,
                        "visibility": "wolf_team",
                    },
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

        alive = self.game_state.get_alive_players()
        await self.information_hub.announce(
            self.locale.get("night_begins", round_number=self.game_state.round_number),
            channel=VisibilityChannel.PUBLIC,
            audience=alive,
            phase="night",
            round_number=self.game_state.round_number,
        )

        messages.append("")

        # Run werewolf discussion phase (if multiple werewolves exist)
        discussion_messages = await self._run_werewolf_discussion()
        messages.extend(discussion_messages)

        def _log_role_acting(player) -> None:
            role_name = player.get_role_name()
            self._log_event(
                EventType.ROLE_ACTING,
                self.locale.get("role_acting", role=role_name, player=player.name),
                data={"player_id": player.player_id, "role": role_name},
            )

        scheduler = NightSkillScheduler(
            self.game_state,
            log_event=self._log_event,
            locale=self.locale,
            resolve_werewolf_votes=self._resolve_werewolf_votes,
            log_role_acting=_log_role_acting,
        )

        pre_wolf_actions, _ = await scheduler.run()
        action_messages = self.process_actions(pre_wolf_actions)
        messages.extend(action_messages)

        werewolf_vote_messages = self._resolve_werewolf_votes()
        messages.extend(werewolf_vote_messages)

        post_wolf_actions = await scheduler.run_post_wolf_resolution()
        action_messages = self.process_actions(post_wolf_actions)
        messages.extend(action_messages)

        death_messages = await self.resolve_deaths()
        messages.extend(death_messages)

        # Narrator: Werewolves sleep (end of night)
        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_sleep"),
            data={"action": "werewolves_sleep"},
        )

        return messages
