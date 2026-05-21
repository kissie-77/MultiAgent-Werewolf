"""Tests for adapter/prompts (legacy re-exports)."""

from llm_werewolf.adapter.prompts import GamePrompts, PlanStrategies, SYSTEM_PROMPT
from llm_werewolf.adapter.prompts.identity import IDENTITY_PROMPTS


def test_system_prompt_chinese() -> None:
    assert "【系统提示】" in SYSTEM_PROMPT
    assert "player_name" in SYSTEM_PROMPT or "{player_name}" in SYSTEM_PROMPT


def test_identity_seer() -> None:
    assert "Seer" in IDENTITY_PROMPTS
    assert "预言" in IDENTITY_PROMPTS["Seer"]["instruction"]


def test_plan_strategies() -> None:
    plan = PlanStrategies.get_plan_by_name("bold")
    assert "plan" in plan


def test_game_prompts_constants() -> None:
    assert GamePrompts.NIGHT_BEGIN == "天黑请闭眼"
