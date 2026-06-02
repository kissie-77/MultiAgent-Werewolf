from llm_werewolf.agent_team.agents.factory import resolve_plan_text, build_system_prompt
from llm_werewolf.game_runtime.prompts.manager import PromptManager


def test_prompt_manager_builds_role_strategy_prompt() -> None:
    prompt = PromptManager.build_role_strategy_prompt(
        seat_number=4, game_role_name="Seer", plan_text="主动报验人信息"
    )

    assert "你的座位号是：4" in prompt
    assert "你的身份是：预言家" in prompt
    assert "主动报验人信息" in prompt
    assert "SpeechDecision" in prompt


def test_agent_team_factory_uses_prompt_manager_contract() -> None:
    prompt = build_system_prompt(8, "Alpha Wolf", "悍跳并制造对立")

    assert prompt == PromptManager.build_role_strategy_prompt(8, "Alpha Wolf", "悍跳并制造对立")
    assert "你的身份是：狼王" in prompt


def test_resolve_plan_text_comes_from_prompt_manager() -> None:
    assert resolve_plan_text("bold", "wolf") == PromptManager.resolve_plan_text("bold", "wolf")


def test_resolve_role_specific_style_plan_text() -> None:
    text = PromptManager.resolve_plan_text("wolf_skeptical", "wolf")

    assert "狼人质疑派打法" in text


def test_role_specific_style_plan_enters_prompt() -> None:
    plan_text = PromptManager.resolve_plan_text("wolf_skeptical", "wolf")
    prompt = PromptManager.build_role_strategy_prompt(
        seat_number=2, game_role_name="Werewolf", plan_text=plan_text
    )

    assert "本局个人计划：" in prompt
    assert "狼人质疑派打法" in prompt
