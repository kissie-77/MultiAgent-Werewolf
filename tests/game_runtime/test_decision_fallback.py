"""Decision fallback policy helpers."""

from unittest.mock import patch

from llm_werewolf.game_runtime.roles import Villager
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.prompts.decision_fallback import select_target_fallback


def test_target_fallback_returns_none_when_random_is_disabled() -> None:
    targets = [Player("player_1", "玩家1", Villager)]

    result = select_target_fallback(targets, allow_random=False, reason="parse_failed")

    assert result.target is None
    assert result.used_random is False
    assert result.reason is None


def test_target_fallback_random_choice_records_reason() -> None:
    targets = [
        Player("player_1", "玩家1", Villager),
        Player("player_2", "玩家2", Villager),
    ]

    with patch(
        "llm_werewolf.game_runtime.prompts.decision_fallback.random.choice",
        return_value=targets[1],
    ):
        result = select_target_fallback(targets, allow_random=True, reason="parse_failed")

    assert result.target is targets[1]
    assert result.used_random is True
    assert result.reason == "parse_failed"
