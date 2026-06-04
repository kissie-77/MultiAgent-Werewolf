"""Hunter / Seer 的 role_data 序列化加宽测试。"""

from llm_werewolf.game_runtime.roles import Seer, Hunter, Villager
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.serialization import (
    serialize_player,
    restore_game_state,
    serialize_game_state,
)


def test_hunter_role_data_serialized() -> None:
    hunter = Player("h1", "Hunter", Hunter)
    hunter.role.ability_uses = 1
    hunter.role.disabled = True

    snap = serialize_player(hunter)

    assert snap.role_data == {"ability_uses": 1, "disabled": True}


def test_seer_role_data_serialized() -> None:
    seer = Player("s1", "Seer", Seer)

    snap = serialize_player(seer)

    assert snap.role_data == {"ability_uses": 0, "disabled": False}


def test_hunter_role_data_roundtrip() -> None:
    hunter = Player("h1", "Hunter", Hunter)
    hunter.role.ability_uses = 1
    state = GameState([hunter, Player("v1", "V1", Villager)])

    snap = serialize_game_state(state)
    restored = restore_game_state(snap)

    restored_hunter = restored.get_player("h1")
    assert restored_hunter.role.ability_uses == 1
