"""引擎控制消息路由的测试。"""

from llm_werewolf.game_runtime.roles import Villager, Werewolf, BloodMoonApostle
from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.events.visibility import RoutedMessage, VisibilityChannel
from llm_werewolf.agent_team.communication.message_router import MessageRouter


def test_public_audience_all_alive() -> None:
    players = [Player("player_1", "玩家1", Villager), Player("player_2", "玩家2", Werewolf)]
    ids = MessageRouter.resolve_audience_player_ids(VisibilityChannel.PUBLIC, players)
    assert set(ids) == {"player_1", "player_2"}


def test_wolf_team_audience() -> None:
    players = [Player("player_1", "玩家1", Villager), Player("player_2", "玩家2", Werewolf)]
    ids = MessageRouter.resolve_audience_player_ids(VisibilityChannel.WOLF_TEAM, players)
    assert ids == ["player_2"]


def test_wolf_team_audience_excludes_untransformed_blood_moon() -> None:
    players = [
        Player("player_1", "玩家1", Werewolf),
        Player("player_2", "玩家2", BloodMoonApostle),
        Player("player_3", "玩家3", Villager),
    ]

    ids = MessageRouter.resolve_audience_player_ids(VisibilityChannel.WOLF_TEAM, players)

    assert ids == ["player_1"]


def test_private_custom_audience_require_actor_or_custom_list() -> None:
    players = [Player("player_1", "玩家1", Villager), Player("player_2", "玩家2", Werewolf)]

    assert MessageRouter.resolve_audience_player_ids(VisibilityChannel.PRIVATE, players) == []
    assert MessageRouter.resolve_audience_player_ids(VisibilityChannel.CUSTOM, players) == []


def test_empty_private_routed_message_is_not_public() -> None:
    routed = RoutedMessage(
        speaker_seat=1,
        speaker_player_id="player_1",
        speaker_name="player_1",
        public_speech="private message",
        channel=VisibilityChannel.PRIVATE,
        audience_player_ids=[],
    )

    assert MessageRouter.visible_to_for_routed(routed, wolf_player_ids=[]) == []


def test_event_type_for_wolf_channel() -> None:
    assert (
        MessageRouter.event_type_for_channel(VisibilityChannel.WOLF_TEAM)
        == EventType.PLAYER_DISCUSSION
    )
