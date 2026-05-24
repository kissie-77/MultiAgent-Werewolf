"""participates_in_wolf_team 与 graveyard_checked 测试。"""

from llm_werewolf.game_runtime.actions.villager import GraveyardKeeperCheckAction
from llm_werewolf.game_runtime.game_state import GameState
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles import GraveyardKeeper, Seer, Villager, Werewolf
from llm_werewolf.game_runtime.roles.names import participates_in_wolf_team
from llm_werewolf.game_runtime.roles.werewolf import BloodMoonApostle
from llm_werewolf.game_runtime.serialization import restore_game_state, serialize_game_state


def test_untransformed_blood_moon_excluded_from_wolf_team() -> None:
    bma = Player("b1", "Apostle", BloodMoonApostle)
    wolf = Player("w1", "Wolf", Werewolf)
    assert not participates_in_wolf_team(bma)
    assert participates_in_wolf_team(wolf)


def test_transformed_blood_moon_in_wolf_team() -> None:
    bma = Player("b1", "Apostle", BloodMoonApostle)
    bma.role.transformed = True
    assert participates_in_wolf_team(bma)


def test_graveyard_checked_persisted_on_execute() -> None:
    keeper = Player("gk", "GK", GraveyardKeeper)
    dead = Player("d1", "Dead", Villager)
    dead.kill()
    state = GameState([keeper, dead])
    state.round_number = 2

    action = GraveyardKeeperCheckAction(keeper, dead, state)
    action.execute()

    assert state.graveyard_checked[2] == "d1"


def test_graveyard_checked_snapshot_roundtrip() -> None:
    players = [Player("v1", "V1", Villager)]
    state = GameState(players)
    state.graveyard_checked[1] = "dead_1"
    snap = serialize_game_state(state)
    assert snap.graveyard_checked == {"1": "dead_1"}

    restored = restore_game_state(snap)
    assert restored.graveyard_checked == {1: "dead_1"}
