"""core/actions 模块的测试。"""

from llm_werewolf.core.actions.villager import SeerCheckAction, WitchPoisonAction, WitchSaveAction
from llm_werewolf.core.actions.werewolf import WerewolfVoteAction
from llm_werewolf.core.game_state import GameState
from llm_werewolf.core.player import Player
from llm_werewolf.core.roles import Seer, Villager, Werewolf, Witch


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
