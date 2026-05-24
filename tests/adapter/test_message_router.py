"""引擎控制消息路由的测试。"""

from llm_werewolf.agent_team.message_router import MessageRouter
from llm_werewolf.agent_team.visibility import VisibilityChannel
from llm_werewolf.core.player import Player
from llm_werewolf.core.roles import Villager, Werewolf
from llm_werewolf.core.types import Camp, EventType


def test_public_audience_all_alive() -> None:
    players = [
        Player("player_1", "玩家1", Villager),
        Player("player_2", "玩家2", Werewolf),
    ]
    ids = MessageRouter.resolve_audience_player_ids(VisibilityChannel.PUBLIC, players)
    assert set(ids) == {"player_1", "player_2"}


def test_wolf_team_audience() -> None:
    players = [
        Player("player_1", "玩家1", Villager),
        Player("player_2", "玩家2", Werewolf),
    ]
    ids = MessageRouter.resolve_audience_player_ids(VisibilityChannel.WOLF_TEAM, players)
    assert ids == ["player_2"]


def test_event_type_for_wolf_channel() -> None:
    assert (
        MessageRouter.event_type_for_channel(VisibilityChannel.WOLF_TEAM)
        == EventType.PLAYER_DISCUSSION
    )
