"""按顺序编排夜间技能（预狼阶段 → 狼票 → 女巫 → 其余角色）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.roles.names import participates_in_wolf_team
from llm_werewolf.game_runtime.registries.role_registry import get_werewolf_roles
from llm_werewolf.game_runtime.registries.role_night_plans import dispatch_night_plan

if TYPE_CHECKING:
    from collections.abc import Callable

    from llm_werewolf.game_runtime.types import PlayerProtocol
    from llm_werewolf.game_runtime.actions.base import Action
    from llm_werewolf.game_runtime.state.game_state import GameState

# 在狼刀目标确定前行动的角色（固定顺序）。
PRE_WOLF_ROLE_NAMES: tuple[str, ...] = (
    "Cupid",
    "Nightmare Wolf",
    "Guard",
    "Guardian Wolf",
    "Thief",
)

WITCH_ROLE_NAMES: frozenset[str] = frozenset({"Witch"})

# 狼刀目标已知后：先女巫，再按此顺序处理其余夜间角色。
POST_WITCH_NIGHT_ROLE_ORDER: tuple[str, ...] = ("Seer", "Graveyard Keeper", "Raven")


class NightSkillScheduler:
    """按标准狼人杀顺序执行夜间技能。"""

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
        """预狼批次，随后收集狼票（旧版合并入口）。"""
        messages: list[str] = []
        pending: list[Action] = []
        pending.extend(await self.run_pre_wolf_phase())
        pending.extend(await self.run_wolf_vote_phase())
        return pending, messages

    async def run_pre_wolf_phase(self) -> list[Action]:
        """丘比特、梦魇狼、守卫等——在狼票之前。"""
        return await self._collect_for_players(self._players_pre_wolf())

    async def run_wolf_vote_phase(self) -> list[Action]:
        """仅收集狼队击杀投票。"""
        return await self._collect_for_players(self._players_werewolf_voters())

    async def run_post_wolf_resolution(self) -> list[Action]:
        """女巫（在 ``werewolf_target`` 确定后），随后预言家 / 守墓人 / 乌鸦。"""
        actions: list[Action] = []
        actions.extend(await self._collect_for_players(self._players_witch()))
        actions.extend(await self._collect_for_players(self._players_post_witch_ordered()))
        return actions

    def _players_pre_wolf(self) -> list[PlayerProtocol]:
        players: list[PlayerProtocol] = []
        for name in PRE_WOLF_ROLE_NAMES:
            if name == "Cupid" and self.game_state.round_number != 1:
                continue
            for player in self.game_state.get_alive_players():
                if (
                    player.get_role_name() == name
                    and player.role.has_night_action(self.game_state)
                    and player not in players
                ):
                    players.append(player)
        return players

    def _players_werewolf_voters(self) -> list[PlayerProtocol]:
        return [
            p
            for p in self.game_state.get_alive_players()
            if p.get_role_name() in self._wolf_role_names
            and p.role.has_night_action(self.game_state)
            and participates_in_wolf_team(p)
        ]

    def _players_witch(self) -> list[PlayerProtocol]:
        return [
            p
            for p in self.game_state.get_alive_players()
            if p.get_role_name() in WITCH_ROLE_NAMES and p.role.has_night_action(self.game_state)
        ]

    def _players_post_witch_ordered(self) -> list[PlayerProtocol]:
        players: list[PlayerProtocol] = []
        handled = set(PRE_WOLF_ROLE_NAMES) | self._wolf_role_names | WITCH_ROLE_NAMES
        for name in POST_WITCH_NIGHT_ROLE_ORDER:
            for player in self.game_state.get_alive_players():
                if (
                    player.get_role_name() == name
                    and player.role.has_night_action(self.game_state)
                    and player not in players
                ):
                    players.append(player)
        for player in self.game_state.get_alive_players():
            if (
                player.get_role_name() not in handled
                and player.role.has_night_action(self.game_state)
                and player not in players
            ):
                players.append(player)
        return players

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
