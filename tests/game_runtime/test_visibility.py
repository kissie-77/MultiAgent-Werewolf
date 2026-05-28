from llm_werewolf.game_runtime.events.visibility import VisibilityChannel, audience_for_channel
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.roles import Villager, Werewolf


def test_wolf_team_audience_only_includes_werewolves() -> None:
    players = [
        Player("player_1", "玩家1", Villager),
        Player("player_2", "玩家2", Werewolf),
        Player("player_3", "玩家3", Werewolf),
    ]
    audience = audience_for_channel(VisibilityChannel.WOLF_TEAM, players)
    assert audience == ["player_2", "player_3"]


def test_public_audience_includes_all_alive() -> None:
    players = [
        Player("player_1", "玩家1", Villager),
        Player("player_2", "玩家2", Werewolf),
    ]
    players[0]._alive = False
    audience = audience_for_channel(VisibilityChannel.PUBLIC, players)
    assert audience == ["player_2"]
