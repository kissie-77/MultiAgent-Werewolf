"""Voting phase logic for the game engine."""

import asyncio
from collections.abc import Callable

from llm_werewolf.core.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.actions import VoteAction
from llm_werewolf.core.game_state import GameState
from llm_werewolf.core.actions.base import Action


class VotingPhaseMixin:
    """Mixin for handling voting phase logic."""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    _handle_elder_penalty: Callable
    _handle_lover_death: Callable
    _handle_wolf_beauty_charm_death: Callable
    _handle_death_abilities: Callable
    build_player_observation: Callable[[PlayerProtocol], str]

    def _build_voting_context(self, player: PlayerProtocol) -> str:
        """Build context for voting phase.

        Args:
            player: The player who will vote.

        Returns:
            str: Context message for the player's agent.
        """
        if not self.game_state:
            return ""

        context_parts = [
            self.build_player_observation(player, include_visible_events=True, include_private_notes=True),
        ]

        # Include player's decision history (safe, no sensitive info)
        if player.agent:
            decision_context = player.agent.get_decision_context()
            if decision_context:
                context_parts.append(decision_context)

        context_parts.append("")
        context_parts.append(
            "Based on the discussion and your role knowledge, "
            "vote for the player you believe should be eliminated."
        )

        return "\n".join(context_parts)

    async def _collect_votes(self) -> list[Action]:
        """Collect votes from all players concurrently.

        Returns:
            list[Action]: List of vote actions.
        """
        if not self.game_state:
            return []

        async def _get_vote(player: PlayerProtocol) -> Action | None:
            """Get a single player's vote."""
            possible_targets = self.game_state.get_alive_players(except_ids=[player.player_id])
            if not possible_targets or not player.agent:
                return None

            try:
                context = self._build_voting_context(player)
                interaction = self.game_state.require_phase_interaction()
                target_player = await interaction.request_seat_choice(
                    player,
                    player.agent,
                    player.get_role_name(),
                    "投票放逐一名玩家",
                    possible_targets,
                    allow_skip=False,
                    additional_context=context,
                    fallback_random=True,
                    round_number=self.game_state.round_number,
                    phase="Voting",
                )

                if target_player:
                    player.agent.add_decision(
                        f"Round {self.game_state.round_number}: Voted for {target_player.name}"
                    )
                    return VoteAction(player, target_player, self.game_state)
            except Exception as e:
                self._log_event(
                    EventType.ERROR,
                    self.locale.get("vote_failed", player=player.name, error=str(e)),
                    data={"player_id": player.player_id, "error": str(e)},
                )
            return None

        voters = [p for p in self.game_state.get_alive_players() if p.can_vote()]
        results = []
        for voter in voters:
            result = await _get_vote(voter)
            results.append(result)
        return [action for action in results if action is not None]

    def _process_votes(self, vote_actions: list[Action]) -> None:
        """Process and log vote actions.

        Args:
            vote_actions: List of vote actions to process.
        """
        for action in vote_actions:
            if action.validate():
                action.execute()
                self._log_event(
                    EventType.VOTE_CAST,
                    self.locale.get(
                        "vote_cast", voter=action.actor.name, target=action.target.name
                    ),
                    data={
                        "voter_id": action.actor.player_id,
                        "voter_name": action.actor.name,
                        "target_id": action.target.player_id,
                        "target_name": action.target.name,
                    },
                )

    def _display_vote_results(self, vote_counts: dict[str, float]) -> None:
        """Display vote results summary.

        Args:
            vote_counts: Dictionary mapping player_id to vote count (float to support sheriff's 1.5 vote).
        """
        if not self.game_state:
            return

        self._log_event(
            EventType.VOTE_RESULT,
            self.locale.get("vote_summary"),
            data={"vote_counts": vote_counts},
        )

        for target_id, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
            target = self.game_state.get_player(target_id)
            if target:
                voters = [
                    self.game_state.get_player(voter_id).name
                    for voter_id, voted_for in self.game_state.votes.items()
                    if voted_for == target_id and self.game_state.get_player(voter_id)
                ]
                voters_str = ", ".join(voters)
                self._log_event(
                    EventType.VOTE_RESULT,
                    self.locale.get(
                        "vote_count", target=target.name, count=count, voters=voters_str
                    ),
                    data={"target_id": target_id, "count": count, "voters": voters},
                )

    def _eliminate_voted_player(self, eliminated: PlayerProtocol) -> None:
        """Eliminate a player who received the most votes.

        Args:
            eliminated: The player to eliminate.
        """
        if not self.game_state:
            return

        eliminated_id = eliminated.player_id

        # Special case: Idiot reveals instead of dying
        if (
            eliminated.role.name == "Idiot"
            and hasattr(eliminated.role, "revealed")
            and not eliminated.role.revealed
        ):
            eliminated.role.revealed = True
            eliminated.disable_voting()
            self._log_event(
                EventType.ROLE_REVEALED,
                self.locale.get("idiot_revealed", player=eliminated.name),
                data={"player_id": eliminated_id, "role": "Idiot"},
            )
            return

        # Normal elimination
        eliminated.kill()
        self.game_state.day_deaths.add(eliminated_id)
        self.game_state.death_causes[eliminated_id] = "vote"

        self._log_event(
            EventType.PLAYER_ELIMINATED,
            self.locale.get(
                "player_eliminated", player=eliminated.name, role=eliminated.get_role_name()
            ),
            data={"player_id": eliminated_id, "role": eliminated.get_role_name()},
        )

        # Handle Elder penalty
        if eliminated.role.name == "Elder":
            self._handle_elder_penalty()
            self._log_event(
                EventType.ROLE_REVEALED,
                self.locale.get("elder_executed"),
                data={"player_id": eliminated_id},
            )

        # Handle cascading deaths
        self._handle_lover_death(eliminated)
        self._handle_wolf_beauty_charm_death(eliminated)

    async def run_voting_phase(self) -> list[str]:
        """Execute the voting phase.

        Returns:
            list[str]: Messages from the voting phase.
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        messages = []
        self.game_state.set_phase(GamePhase.DAY_VOTING)
        messages.append("\n=== Voting Phase ===")

        # Collect and process votes
        vote_actions = await self._collect_votes()
        self._process_votes(vote_actions)

        vote_counts = self.game_state.get_vote_counts()

        if vote_counts:
            self._display_vote_results(vote_counts)

            # Determine elimination
            max_votes = max(vote_counts.values())
            candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

            if len(candidates) == 1:
                eliminated = self.game_state.get_player(candidates[0])
                if eliminated:
                    self._eliminate_voted_player(eliminated)
            else:
                self._log_event(EventType.VOTE_RESULT, self.locale.get("vote_tied"), data={})
        else:
            self._log_event(EventType.VOTE_RESULT, self.locale.get("no_votes"), data={})

        death_ability_messages = await self._handle_death_abilities()
        messages.extend(death_ability_messages)

        return messages
