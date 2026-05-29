from llm_werewolf.game_runtime.seat import get_player_seat, resolve_player_by_seat
from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.state.player import Player


def test_get_player_seat_uses_runtime_player_id() -> None:
    assert get_player_seat(Player("player_7", "Alice", Villager)) == 7


def test_get_player_seat_can_fallback_to_player_name() -> None:
    assert get_player_seat(Player("seat-a", "玩家4", Werewolf)) == 4


def test_resolve_player_by_seat_uses_global_seat_number() -> None:
    targets = [Player("player_2", "玩家2", Villager), Player("player_4", "玩家4", Werewolf)]

    assert resolve_player_by_seat(4, targets) is targets[1]
    assert resolve_player_by_seat(3, targets) is None
