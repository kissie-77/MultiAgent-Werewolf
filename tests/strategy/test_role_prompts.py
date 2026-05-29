from llm_werewolf.strategy.role_prompts import GamePrompts, RolePrompts, PlanStrategies


def test_role_strategy_prompt_is_canonical() -> None:
    assert "多 Agent 狼人杀博弈" in RolePrompts.BASE_PROMPT
    assert "信息边界" in RolePrompts.BASE_PROMPT
    assert "阵营" in RolePrompts.WOLF["role_instruction"]


def test_game_prompts_and_plan_strategies_available() -> None:
    assert GamePrompts.NIGHT_BEGIN == "天黑请闭眼"
    assert PlanStrategies.get_plan_by_name("bold")["name"] == "bold"
