"""core/engine/action_processor.py 的测试。"""

from unittest.mock import MagicMock

from llm_werewolf.core.actions.villager import GuardProtectAction, SeerCheckAction, WitchSaveAction
from llm_werewolf.core.actions.werewolf import NightmareWolfBlockAction, WerewolfVoteAction
from llm_werewolf.core.engine.action_processor import ActionProcessorMixin
from llm_werewolf.core.game_state import GameState
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.player import Player
from llm_werewolf.core.roles import Guard, NightmareWolf, Seer, Villager, Werewolf, Witch
from llm_werewolf.core.types import ActionPriority


class _Processor(ActionProcessorMixin):
    def __init__(self, game_state: GameState) -> None:
        self.game_state = game_state
        self.locale = Locale("en-US")
        self._log_event = MagicMock()


def test_get_action_priority_order() -> None:
    guard = GuardProtectAction(
        Player("g1", "Guard", Guard),
        Player("v1", "Villager", Villager),
        GameState([]),
    )
    werewolf_vote = WerewolfVoteAction(
        Player("w1", "Wolf", Werewolf),
        Player("v1", "Villager", Villager),
        GameState([]),
    )
    seer_check = SeerCheckAction(
        Player("s1", "Seer", Seer),
        Player("v1", "Villager", Villager),
        GameState([]),
    )

    assert ActionProcessorMixin._get_action_priority(guard) == ActionPriority.GUARD.value
    assert (
        ActionProcessorMixin._get_action_priority(werewolf_vote) == ActionPriority.WEREWOLF.value
    )
    assert ActionProcessorMixin._get_action_priority(seer_check) == ActionPriority.SEER.value


def test_is_actor_blocked_excludes_nightmare_block_action() -> None:
    nightmare = Player("n1", "Nightmare", NightmareWolf)
    seer = Player("s1", "Seer", Seer)
    villager = Player("v1", "Villager", Villager)
    state = GameState([nightmare, seer, villager])
    state.nightmare_blocked = "s1"
    processor = _Processor(state)

    blocked_action = SeerCheckAction(seer, villager, state)
    block_action = NightmareWolfBlockAction(nightmare, villager, state)

    assert processor._is_actor_blocked(blocked_action) is True
    assert processor._is_actor_blocked(block_action) is False


def test_log_witch_save_action() -> None:
    witch = Player("w1", "Witch", Witch)
    target = Player("v1", "Villager", Villager)
    state = GameState([witch, target])
    state.round_number = 1
    processor = _Processor(state)

    action = WitchSaveAction(witch, target, state)
    processor._log_witch_save_action(action)

    processor._log_event.assert_called_once()
