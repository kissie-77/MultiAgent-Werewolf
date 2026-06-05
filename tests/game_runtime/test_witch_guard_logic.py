"""女巫 / 守卫夜间逻辑专项测试。

覆盖：
- 单独守卫保护 → 刀口存活
- 单独女巫解药 → 刀口存活
- 守卫 + 女巫同夜同救（毒奶）→ 刀口仍死亡
- 无保护 → 刀口死亡
- 女巫毒药结算与 death_causes
- 守卫不能连续两夜保护同一人
- resolve_deaths 端到端结算
"""

from __future__ import annotations

import pytest

from llm_werewolf.game_runtime.actions.villager import (
    GuardProtectAction,
    WitchPoisonAction,
    WitchSaveAction,
)
from llm_werewolf.game_runtime.death_abilities import DEATH_ABILITY_ROLE_NAMES
from llm_werewolf.game_runtime.engine.death_handler import DeathHandlerMixin
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.roles import Guard, Hunter, Villager, Werewolf, Witch
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.types import GamePhase


class _StubDeathHandler(DeathHandlerMixin):
    def __init__(self, game_state: GameState) -> None:
        self.game_state = game_state
        self.locale = Locale("zh-CN")
        self.events: list[tuple] = []

    def _log_event(self, event_type, message: str = "", *, data=None, **kwargs) -> None:  # noqa: ANN001
        self.events.append((event_type, message, data or {}))


def _night_state(*players: Player, werewolf_target: str) -> GameState:
    state = GameState(list(players))
    state.phase = GamePhase.NIGHT
    state.round_number = 1
    state.werewolf_target = werewolf_target
    return state


def _victim() -> Player:
    return Player("v1", "Victim", Villager)


# ── 狼刀结算：守卫 / 女巫优先级 ───────────────────────────────────────────

def test_werewolf_kill_guard_only_target_survives() -> None:
    victim = _victim()
    state = _night_state(victim, werewolf_target="v1")
    state.guard_protected = "v1"

    handler = _StubDeathHandler(state)
    handler._handle_werewolf_kill(victim)

    assert victim.is_alive()
    assert "v1" not in state.night_deaths


def test_werewolf_kill_witch_save_only_target_survives() -> None:
    victim = _victim()
    state = _night_state(victim, werewolf_target="v1")
    state.witch_saved_target = "v1"

    handler = _StubDeathHandler(state)
    handler._handle_werewolf_kill(victim)

    assert victim.is_alive()
    assert "v1" not in state.night_deaths


def test_werewolf_kill_guard_and_witch_same_target_dies() -> None:
    """毒奶：守卫与女巫同夜同救刀口，目标仍会死亡。"""
    victim = _victim()
    state = _night_state(victim, werewolf_target="v1")
    state.guard_protected = "v1"
    state.witch_saved_target = "v1"

    handler = _StubDeathHandler(state)
    handler._handle_werewolf_kill(victim)

    assert not victim.is_alive()
    assert "v1" in state.night_deaths
    assert state.death_causes["v1"] == "guard_witch_conflict"
    assert any("毒奶" in msg for _, msg, _ in handler.events)


def test_werewolf_kill_no_protection_target_dies() -> None:
    victim = _victim()
    state = _night_state(victim, werewolf_target="v1")

    handler = _StubDeathHandler(state)
    handler._handle_werewolf_kill(victim)

    assert not victim.is_alive()
    assert "v1" in state.night_deaths


@pytest.mark.asyncio
async def test_resolve_deaths_guard_witch_conflict_end_to_end() -> None:
    victim = _victim()
    state = _night_state(victim, werewolf_target="v1")
    state.guard_protected = "v1"
    state.witch_saved_target = "v1"

    handler = _StubDeathHandler(state)
    await handler.resolve_deaths()

    assert not victim.is_alive()
    assert state.death_causes["v1"] == "guard_witch_conflict"


# ── 女巫行动校验 ───────────────────────────────────────────────────────────

def test_witch_save_rejects_non_werewolf_target() -> None:
    witch = Player("w1", "Witch", Witch)
    target = Player("v1", "Target", Villager)
    state = GameState([witch, target])
    state.werewolf_target = "v2"

    action = WitchSaveAction(witch, target, state)
    assert action.validate() is False


def test_witch_save_rejects_when_no_save_potion() -> None:
    witch = Player("w1", "Witch", Witch)
    target = Player("v1", "Target", Villager)
    state = GameState([witch, target])
    state.werewolf_target = "v1"
    witch.role.has_save_potion = False

    action = WitchSaveAction(witch, target, state)
    assert action.validate() is False


def test_witch_poison_sets_death_cause_and_kills() -> None:
    witch = Player("w1", "Witch", Witch)
    victim = Player("v1", "Victim", Villager)
    state = GameState([witch, victim])
    state.witch_poison_target = "v1"

    handler = _StubDeathHandler(state)
    handler._resolve_witch_poison_death()

    assert not victim.is_alive()
    assert "v1" in state.night_deaths
    assert state.death_causes["v1"] == "witch_poison"


@pytest.mark.asyncio
async def test_witch_poison_blocks_hunter_death_ability() -> None:
    """被女巫毒杀的猎人不能发动开枪技能。"""
    hunter = Player("h1", "Hunter", Hunter)
    witch = Player("w1", "Witch", Witch)
    state = GameState([hunter, witch])
    state.witch_poison_target = "h1"
    state.night_deaths.add("h1")
    state.death_causes["h1"] = "witch_poison"
    hunter.kill()

    assert hunter.role.name in DEATH_ABILITY_ROLE_NAMES

    handler = _StubDeathHandler(state)
    messages = await handler._handle_death_abilities()

    assert "h1" in state.death_abilities_used
    assert messages == []
    assert any("毒杀" in msg for _, msg, _ in handler.events)


# ── 守卫行动校验 ───────────────────────────────────────────────────────────

def test_guard_cannot_protect_same_target_two_nights_in_row() -> None:
    guard = Player("g1", "Guard", Guard)
    target = Player("v1", "Target", Villager)
    state = GameState([guard, target])
    guard.role.last_protected = "v1"

    action = GuardProtectAction(guard, target, state)
    assert action.validate() is False


def test_guard_protect_updates_state() -> None:
    guard = Player("g1", "Guard", Guard)
    target = Player("v1", "Target", Villager)
    state = GameState([guard, target])

    action = GuardProtectAction(guard, target, state)
    assert action.validate() is True
    action.execute()

    assert state.guard_protected == "v1"
    assert guard.role.last_protected == "v1"
