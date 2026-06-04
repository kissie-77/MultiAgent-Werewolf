"""game_runtime/engine/action_processor.py 的测试。"""

from unittest.mock import MagicMock

from llm_werewolf.game_runtime.roles import (
    Seer,
    Guard,
    Witch,
    Raven,
    Villager,
    Werewolf,
    WolfBeauty,
    WhiteWolf,
    NightmareWolf,
    GuardianWolf,
)
from llm_werewolf.game_runtime.types import EventType, ActionPriority
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.actions.werewolf import (
    WerewolfVoteAction,
    WhiteWolfKillAction,
    WolfBeautyCharmAction,
    NightmareWolfBlockAction,
    GuardianWolfProtectAction,
)
from llm_werewolf.game_runtime.actions.villager import (
    SeerCheckAction,
    WitchSaveAction,
    WitchPoisonAction,
    GuardProtectAction,
    RavenMarkAction,
)
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.engine.action_processor import ActionProcessorMixin


class _Processor(ActionProcessorMixin):
    def __init__(self, game_state: GameState) -> None:
        self.game_state = game_state
        self.locale = Locale("en-US")
        self._log_event = MagicMock()


def test_get_action_priority_order() -> None:
    guard = GuardProtectAction(
        Player("g1", "Guard", Guard), Player("v1", "Villager", Villager), GameState([])
    )
    werewolf_vote = WerewolfVoteAction(
        Player("w1", "Wolf", Werewolf), Player("v1", "Villager", Villager), GameState([])
    )
    seer_check = SeerCheckAction(
        Player("s1", "Seer", Seer), Player("v1", "Villager", Villager), GameState([])
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


def test_decision_data_prefers_action_metadata_over_agent_cache() -> None:
    witch = Player("player_1", "Witch", Witch)
    old_target = Player("player_2", "Old", Villager)
    new_target = Player("player_3", "New", Villager)
    state = GameState([witch, old_target, new_target])
    agent = MagicMock()
    agent._last_decision_metadata = {
        "decision_seat": 2,
        "resolved_target_id": "player_2",
    }
    witch.agent = agent
    action = WitchPoisonAction(witch, new_target, state)
    action._decision_metadata = {
        "decision_seat": 3,
        "resolved_target_id": "player_3",
    }

    assert ActionProcessorMixin._decision_data(action) == {
        "decision": {
            "decision_seat": 3,
            "resolved_target_id": "player_3",
        }
    }


def test_log_white_wolf_action_emits_typed_event() -> None:
    white = Player("w1", "White", WhiteWolf)
    target = Player("w2", "Wolf", Werewolf)
    state = GameState([white, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_white_wolf_action(WhiteWolfKillAction(white, target, state))

    event_type, _message = processor._log_event.call_args.args[:2]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.WHITE_WOLF_KILLED
    assert data["actor_id"] == "w1"
    assert data["target_id"] == "w2"
    assert data["result"] == "killed"


def test_log_wolf_beauty_action_emits_typed_event() -> None:
    beauty = Player("b1", "Beauty", WolfBeauty)
    target = Player("v1", "Villager", Villager)
    state = GameState([beauty, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_wolf_beauty_action(WolfBeautyCharmAction(beauty, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.WOLF_BEAUTY_CHARMED
    assert data["actor_id"] == "b1"
    assert data["target_id"] == "v1"
    assert data["result"] == "charmed"


def test_log_nightmare_block_action_emits_typed_event() -> None:
    nightmare = Player("n1", "Nightmare", NightmareWolf)
    target = Player("s1", "Seer", Seer)
    state = GameState([nightmare, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_nightmare_block_action(NightmareWolfBlockAction(nightmare, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.NIGHTMARE_BLOCKED
    assert data["actor_id"] == "n1"
    assert data["target_id"] == "s1"
    assert data["result"] == "blocked"


def test_log_guardian_wolf_action_emits_typed_event() -> None:
    guardian = Player("g1", "Guardian", GuardianWolf)
    target = Player("w2", "Wolf", Werewolf)
    state = GameState([guardian, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_guardian_wolf_action(GuardianWolfProtectAction(guardian, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.GUARDIAN_WOLF_PROTECTED
    assert data["actor_id"] == "g1"
    assert data["target_id"] == "w2"
    assert data["result"] == "protected"


def test_log_raven_action_emits_typed_event() -> None:
    raven = Player("r1", "Raven", Raven)
    target = Player("v1", "Villager", Villager)
    state = GameState([raven, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_raven_action(RavenMarkAction(raven, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.RAVEN_MARKED
    assert data["actor_id"] == "r1"
    assert data["target_id"] == "v1"
    assert data["result"] == "marked"
