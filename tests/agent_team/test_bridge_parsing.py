"""遗留路径：解析位于 WerewolfAdapterBridge（ActionSelector 已移除）。"""

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.strategy.phase_outputs import ActionPhase


def test_target_selection_uses_player_seat_not_list_position() -> None:
    targets = [
        Player("player_2", "玩家2", Villager),
        Player("player_4", "玩家4", Villager),
        Player("player_5", "玩家5", Villager),
    ]

    selected = WerewolfAdapterBridge.parse_target_selection("[[2]]", targets)

    assert selected is targets[0]
    assert selected.player_id == "player_2"


def test_target_selection_rejects_illegal_seat() -> None:
    targets = [Player("player_2", "玩家2", Villager), Player("player_4", "玩家4", Villager)]

    assert WerewolfAdapterBridge.parse_target_selection("[[3]]", targets) is None


def test_target_selection_can_parse_seat_from_player_name() -> None:
    targets = [Player("seat-a", "玩家2", Villager), Player("seat-b", "玩家4", Werewolf)]

    selected = WerewolfAdapterBridge.parse_target_selection("4", targets)

    assert selected is targets[1]


def test_target_selection_allows_zero_skip() -> None:
    targets = [Player("player_2", "玩家2", Villager)]

    assert WerewolfAdapterBridge.parse_target_selection("[[0]]", targets, allow_skip=True) is None


def test_yes_no_accepts_bracketed_binary_answers() -> None:
    assert WerewolfAdapterBridge.parse_yes_no("[[1]]")
    assert not WerewolfAdapterBridge.parse_yes_no("[[0]]")


def test_yes_no_rejects_ambiguous_substrings() -> None:
    import pytest

    with pytest.raises(Exception):
        WerewolfAdapterBridge.parse_yes_no("I know")


def test_day_vote_prompt_does_not_include_role_night_action() -> None:
    targets = [Player("player_2", "玩家2", Villager), Player("player_3", "玩家3", Werewolf)]

    prompt = WerewolfAdapterBridge.build_target_selection_prompt(
        "Seer",
        "请投票选择你想淘汰的玩家",
        targets,
        allow_skip=True,
        action_phase=ActionPhase.DAY_VOTE,
    )

    assert "预言家请睁眼" not in prompt
    assert "请投票选择你想淘汰的玩家" in prompt


def test_sheriff_vote_prompt_does_not_include_role_night_action() -> None:
    targets = [Player("player_2", "玩家2", Villager), Player("player_3", "玩家3", Werewolf)]

    prompt = WerewolfAdapterBridge.build_target_selection_prompt(
        "Villager",
        "请投票选择你想支持的警长候选人",
        targets,
        allow_skip=True,
        action_phase=ActionPhase.SHERIFF_VOTE,
    )

    assert "预言家请睁眼" not in prompt
    assert "请投票选择你想支持的警长候选人" in prompt
