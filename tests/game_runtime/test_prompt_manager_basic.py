"""统一提示管理器的测试。"""

from llm_werewolf.game_runtime.roles.catalog import get_definition
from llm_werewolf.game_runtime.prompts import PromptManager


def test_system_and_identity_messages() -> None:
    definition = get_definition("Seer")
    history = PromptManager.build_initial_chat_history(
        definition, player_name="玩家A", seat_number=3, plan="谨慎"
    )
    assert len(history) == 2
    assert history[0]["role"] == "system"
    assert "【系统提示】" in history[0]["content"]
    assert "玩家A" in history[0]["content"]
    assert history[1]["role"] == "system"
    assert "【身份提示】" in history[1]["content"]
    assert "预言家" in history[1]["content"]


def test_target_prompt_chinese_brackets() -> None:
    class Target:
        name = "Bob"

    prompt = PromptManager.build_target_selection_prompt(
        "预言家", "查验一名玩家", [Target()], round_number=1, phase="夜晚"
    )
    assert "[[2]]" in prompt or "[[]]" in prompt
    assert "可选目标" in prompt
    assert "ONLY" not in prompt


def test_parse_bracket_number() -> None:
    assert PromptManager.parse_bracket_number("我选择 [[3]]") == 3
    assert PromptManager.parse_yes_no("[[1]]") is True
    assert PromptManager.parse_yes_no("[[0]]") is False
