"""Ordered night-skill orchestration (guard → wolf votes → witch → others)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from llm_werewolf.core.role_night_plans import dispatch_night_plan
from llm_werewolf.core.role_registry import get_werewolf_roles
from llm_werewolf.core.types import EventType

if TYPE_CHECKING:
    from llm_werewolf.core.actions.base import Action
    from llm_werewolf.core.game_state import GameState
    from llm_werewolf.core.types import PlayerProtocol

# Roles that act before wolf kill target is finalized.
PRE_WOLF_ROLE_NAMES: tuple[str, ...] = (
    "Cupid",
    "Nightmare Wolf",
    "Guard",
    "Guardian Wolf",
    "Thief",
)

WITCH_ROLE_NAMES: frozenset[str] = frozenset({"Witch"})


class NightSkillScheduler:
    """Runs night skills in standard werewolf order."""

    def __init__(
        self,
        game_state: GameState,
        *,
        log_event: Callable,
        locale: object,
        resolve_werewolf_votes: Callable[[], list[str]],
        log_role_acting: Callable[[PlayerProtocol], None] | None = None,
    ) -> None:
        self.game_state = game_state
        self._log_event = log_event
        self.locale = locale
        self._resolve_werewolf_votes = resolve_werewolf_votes
        self._log_role_acting = log_role_acting
        self._wolf_role_names = get_werewolf_roles()

    async def run(self) -> tuple[list[Action], list[str]]:
        """Collect and partially process night actions in skill order.

        Returns:
            Tuple of (actions still to process, status messages).
        """
        messages: list[str] = []
        pending: list[Action] = []

        batch_pre_wolf = await self._collect_for_players(self._players_pre_wolf())
        pending.extend(batch_pre_wolf)

        batch_wolf = await self._collect_for_players(self._players_werewolf_voters())
        pending.extend(batch_wolf)

        return pending, messages

    async def run_post_wolf_resolution(self) -> list[Action]:
        """Collect witch and remaining night actions after ``werewolf_target`` is set."""
        actions: list[Action] = []
        actions.extend(await self._collect_for_players(self._players_witch()))
        actions.extend(await self._collect_for_players(self._remaining_night_actors()))
        return actions

    def _players_pre_wolf(self) -> list[PlayerProtocol]:
        players = []
        for name in PRE_WOLF_ROLE_NAMES:
            if name == "Cupid" and self.game_state.round_number != 1:
                continue
            for player in self.game_state.get_alive_players():
                if player.get_role_name() == name and player.role.has_night_action(self.game_state):
                    players.append(player)
        return players

    def _players_werewolf_voters(self) -> list[PlayerProtocol]:
        return [
            p
            for p in self.game_state.get_alive_players()
            if p.get_role_name() in self._wolf_role_names
            and p.role.has_night_action(self.game_state)
        ]

    def _players_witch(self) -> list[PlayerProtocol]:
        return [
            p
            for p in self.game_state.get_alive_players()
            if p.get_role_name() in WITCH_ROLE_NAMES
            and p.role.has_night_action(self.game_state)
        ]

    def _remaining_night_actors(self) -> list[PlayerProtocol]:
        handled = set(PRE_WOLF_ROLE_NAMES) | self._wolf_role_names | WITCH_ROLE_NAMES
        return [
            p
            for p in self.game_state.get_alive_players()
            if p.get_role_name() not in handled
            and p.role.has_night_action(self.game_state)
        ]

    async def _collect_for_players(self, players: list[PlayerProtocol]) -> list[Action]:
        actions: list[Action] = []
        interaction = self.game_state.require_phase_interaction()
        for player in players:
            if self._log_role_acting:
                self._log_role_acting(player)
            try:
                result = await self._plan_for_player(player, interaction)
                if result:
                    actions.extend(result)
            except Exception as e:
                self._log_event(
                    EventType.ERROR,
                    self.locale.get(
                        "night_action_failed",
                        player=player.name,
                        role=player.get_role_name(),
                        error=str(e),
                    ),
                    data={
                        "player_id": player.player_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
        return actions

    async def _plan_for_player(self, player: PlayerProtocol, interaction: object) -> list[Action]:
        return await dispatch_night_plan(player.role, self.game_state, interaction)
