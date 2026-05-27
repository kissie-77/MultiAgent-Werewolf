"""game_runtime/actions 模块的测试。"""

from llm_werewolf.game_runtime.actions.villager import SeerCheckAction, WitchPoisonAction, WitchSaveAction
from llm_werewolf.game_runtime.actions.werewolf import WhiteWolfKillAction, WerewolfVoteAction
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.roles import Seer, Villager, Werewolf, Witch
from llm_werewolf.game_runtime.roles.werewolf import HiddenWolf, WhiteWolf
from llm_werewolf.game_runtime.roles.names import seer_apparent_camp
from llm_werewolf.game_runtime.types import Camp


def test_witch_save_validate_and_execute() -> None:
    witch = Player("w1", "Witch", Witch)
    target = Player("v1", "Target", Villager)
    state = GameState([witch, target])
    state.werewolf_target = "v1"

    action = WitchSaveAction(witch, target, state)
    assert action.validate() is True
    messages = action.execute()
    assert "Witch saves" in messages[0]
    assert state.witch_saved_target == "v1"
    assert witch.role.has_save_potion is False


def test_witch_poison_validate() -> None:
    witch = Player("w1", "Witch", Witch)
    target = Player("v1", "Target", Villager)
    state = GameState([witch, target])
    witch.role.has_save_potion = False

    action = WitchPoisonAction(witch, target, state)
    assert action.validate() is True
    action.execute()
    assert state.witch_poison_target == "v1"


def test_seer_check_execute_records_round() -> None:
    seer = Player("s1", "Seer", Seer)
    wolf = Player("w1", "Wolf", Werewolf)
    state = GameState([seer, wolf])
    state.round_number = 2

    action = SeerCheckAction(seer, wolf, state)
    assert action.validate() is True
    action.execute()
    assert state.seer_checked[2] == "w1"


def test_werewolf_vote_action() -> None:
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    state = GameState([wolf, villager])

    action = WerewolfVoteAction(wolf, villager, state)
    assert action.validate() is True
    action.execute()
    assert state.werewolf_votes["w1"] == "v1"


def test_werewolf_vote_rejects_wolf_target() -> None:
    wolf1 = Player("w1", "Wolf1", Werewolf)
    wolf2 = Player("w2", "Wolf2", Werewolf)
    state = GameState([wolf1, wolf2])

    action = WerewolfVoteAction(wolf1, wolf2, state)
    assert action.validate() is False


def test_seer_hidden_wolf_appears_villager() -> None:
    hidden = Player("h1", "Hidden", HiddenWolf)
    assert seer_apparent_camp(hidden) == Camp.VILLAGER

    action = SeerCheckAction(Player("s1", "Seer", Seer), hidden, GameState([hidden]))
    messages = action.execute()
    assert "villager" in messages[0]


def test_white_wolf_kill_validate_uses_role_config_name() -> None:
    white_wolf = Player("ww1", "WhiteWolf", WhiteWolf)
    teammate = Player("w1", "Wolf", Werewolf)
    state = GameState([white_wolf, teammate])
    state.round_number = 1

    action = WhiteWolfKillAction(white_wolf, teammate, state)
    assert action.validate() is True
