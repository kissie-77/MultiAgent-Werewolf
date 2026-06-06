"""游戏流程 Prompt 与角色策略常量的测试。"""

from llm_werewolf.strategy.registry.role_prompts import GamePrompts, PlanStrategies
from llm_werewolf.game_runtime.prompts.system import SYSTEM_PROMPT
from llm_werewolf.game_runtime.prompts.identity import IDENTITY_PROMPTS


def test_system_prompt_chinese() -> None:
    assert "【系统提示】" in SYSTEM_PROMPT
    assert "player_name" in SYSTEM_PROMPT or "{player_name}" in SYSTEM_PROMPT


def test_identity_seer() -> None:
    assert "Seer" in IDENTITY_PROMPTS
    assert "预言" in IDENTITY_PROMPTS["Seer"]["instruction"]


def test_plan_strategies() -> None:
    plan = PlanStrategies.get_plan_by_name("bold")
    assert plan["name"] == "bold"
    assert "wolf" in plan


def test_role_specific_style_plan_strategy() -> None:
    plan = PlanStrategies.get_plan_by_name("wolf_skeptical")

    assert plan["name"] == "wolf_skeptical"
    assert "wolf" in plan
    assert "狼人质疑派打法" in plan["wolf"]


def test_default_role_style_plan_names() -> None:
    assert PlanStrategies.default_role_style_plan_names("wolf") == [
        "wolf_conservative",
        "wolf_aggressive",
        "wolf_skeptical",
        "wolf_coordinator",
    ]


def test_game_prompts_constants() -> None:
    assert GamePrompts.NIGHT_BEGIN == "天黑请闭眼"
