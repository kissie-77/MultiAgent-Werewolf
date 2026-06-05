"""死亡链传播回归测试。

覆盖场景：
1. wolf_beauty_charmed 跨轮必须被清空（状态泄漏修复验证）
2. 被魅惑玩家若是情侣，其伴侣也随之殉情
3. 情侣死亡后，其伴侣的死亡加入 night_deaths/day_deaths，
   使 _handle_death_abilities 可继续处理（猎人开枪链）
"""

from __future__ import annotations

from typing import Callable
from unittest.mock import MagicMock

from llm_werewolf.game_runtime.engine.death_handler import DeathHandlerMixin
from llm_werewolf.game_runtime.i18n.locale import Locale
from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.roles.werewolf import WolfBeauty
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.types import GamePhase


# ── 测试用 DeathHandler stub ──────────────────────────────────────────────

class _StubDeathHandler(DeathHandlerMixin):
    def __init__(self, game_state: GameState) -> None:
        self.game_state = game_state
        self.locale = Locale("zh-CN")
        self.events: list[tuple] = []

    def _log_event(self, event_type, message: str = "", *, data=None, **kwargs) -> None:  # noqa: ANN001
        self.events.append((event_type, message, data or {}))


def _make_player(pid: str, name: str, role_cls=Villager) -> Player:  # noqa: ANN001
    return Player(pid, name, role_cls)


def _make_state_in_night(*players: Player) -> GameState:
    state = GameState(list(players))
    state.phase = GamePhase.NIGHT
    state.round_number = 1
    return state


# ── 1. wolf_beauty_charmed 跨轮清空 ───────────────────────────────────────

def test_wolf_beauty_charmed_cleared_on_next_round() -> None:
    """DAY_VOTING → NIGHT 转换必须清除 wolf_beauty_charmed。"""
    state = GameState([_make_player("p1", "Wolf", Werewolf), _make_player("p2", "Villager")])
    state.phase = GamePhase.DAY_VOTING
    state.wolf_beauty_charmed = "p2"

    state.next_phase()

    assert state.phase == GamePhase.NIGHT
    assert state.wolf_beauty_charmed is None, "跨轮后 wolf_beauty_charmed 应被清空"


def test_wolf_beauty_charmed_not_cleared_within_round() -> None:
    """同一轮内（NIGHT→DAY_DISCUSSION）不应清除 wolf_beauty_charmed。"""
    state = GameState([_make_player("p1", "Wolf", Werewolf), _make_player("p2", "Villager")])
    state.phase = GamePhase.NIGHT
    state.round_number = 1
    state.sheriff_election_done = True
    state.wolf_beauty_charmed = "p2"

    state.next_phase()

    assert state.phase == GamePhase.DAY_DISCUSSION
    assert state.wolf_beauty_charmed == "p2", "同轮内魅惑状态应保留"


# ── 2. 魅惑死亡 → 情侣传播 ───────────────────────────────────────────────

def test_charm_death_propagates_to_lover() -> None:
    """被魅惑玩家死亡时，其情侣伴侣也应殉情。"""
    wolf_beauty = _make_player("wb", "WolfBeauty", WolfBeauty)
    charmed = _make_player("c1", "Charmed")
    lover = _make_player("l1", "Lover")

    # 建立情侣关系
    charmed.set_lover("l1")
    lover.set_lover("c1")

    state = _make_state_in_night(wolf_beauty, charmed, lover)
    state.wolf_beauty_charmed = "c1"

    # 杀死狼美人
    wolf_beauty.kill()
    state.night_deaths.add("wb")

    handler = _StubDeathHandler(state)
    handler._resolve_wolf_beauty_charm_deaths()

    assert not charmed.is_alive(), "被魅惑玩家应随狼美人死亡"
    assert not lover.is_alive(), "被魅惑玩家的情侣应随之殉情"
    assert "c1" in state.night_deaths
    assert "l1" in state.night_deaths


def test_charm_death_no_lover_does_not_crash() -> None:
    """被魅惑玩家无情侣时，死亡链应正常终止，不报错。"""
    wolf_beauty = _make_player("wb", "WolfBeauty", WolfBeauty)
    charmed = _make_player("c1", "Charmed")

    state = _make_state_in_night(wolf_beauty, charmed)
    state.wolf_beauty_charmed = "c1"

    wolf_beauty.kill()
    state.night_deaths.add("wb")

    handler = _StubDeathHandler(state)
    handler._resolve_wolf_beauty_charm_deaths()

    assert not charmed.is_alive()
    assert "c1" in state.night_deaths


# ── 3. 情侣殉情后死亡加入集合供后续 ability 处理 ──────────────────────────

def test_lover_death_added_to_night_deaths_for_ability_processing() -> None:
    """情侣殉情后应加入 night_deaths，使 _handle_death_abilities 可以处理其死亡技能。"""
    wolf_beauty = _make_player("wb", "WolfBeauty", WolfBeauty)
    charmed = _make_player("c1", "Charmed")
    lover = _make_player("l1", "Lover")

    charmed.set_lover("l1")
    lover.set_lover("c1")

    state = _make_state_in_night(wolf_beauty, charmed, lover)
    state.wolf_beauty_charmed = "c1"

    wolf_beauty.kill()
    state.night_deaths.add("wb")

    handler = _StubDeathHandler(state)
    handler._resolve_wolf_beauty_charm_deaths()

    # 情侣的 player_id 必须在 night_deaths 中，否则猎人等技能无法被触发
    assert "l1" in state.night_deaths, "情侣伴侣 l1 应在 night_deaths 中，供后续 death ability 处理"


def test_direct_lover_death_in_day_phase_adds_to_day_deaths() -> None:
    """白天情侣死亡时，伴侣死亡应加入 day_deaths，而非 night_deaths。"""
    p1 = _make_player("p1", "P1")
    p2 = _make_player("p2", "P2")
    p1.set_lover("p2")
    p2.set_lover("p1")

    state = GameState([p1, p2])
    state.phase = GamePhase.DAY_VOTING

    # 直接杀死 p1
    p1.kill()
    state.day_deaths.add("p1")

    handler = _StubDeathHandler(state)
    handler._handle_lover_death(p1)

    assert not p2.is_alive(), "白天情侣死亡应触发伴侣殉情"
    assert "p2" in state.day_deaths, "白天殉情应加入 day_deaths"
    assert "p2" not in state.night_deaths
