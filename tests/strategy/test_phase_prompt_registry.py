"""Tests for externalized phase/plan prompt packages."""

from llm_werewolf.strategy.phase_prompt_registry import (
    load_phase_prompts,
    load_plan_bundle,
    load_seat_action_map,
    resolve_latest_phase_version,
    resolve_latest_plan_version,
)
from llm_werewolf.strategy.role_prompts import GamePrompts, PlanStrategies, ROLE_SEAT_ACTION


def test_phase_prompts_loaded_from_yaml() -> None:
    prompts = load_phase_prompts(resolve_latest_phase_version())
    assert prompts["NIGHT_BEGIN"] == "天黑请闭眼"
    assert GamePrompts.NIGHT_BEGIN == "天黑请闭眼"
    assert "SpeechDecision" in GamePrompts.SPEECH_PROMPT


def test_seat_action_map_resolves_prompt_keys() -> None:
    seat_map = load_seat_action_map(resolve_latest_phase_version())
    assert seat_map["Werewolf"] == GamePrompts.WOLF_OPEN
    assert ROLE_SEAT_ACTION["Alpha Wolf"] == GamePrompts.WOLF_OPEN
    assert "SeatChoiceDecision" in ROLE_SEAT_ACTION["Graveyard Keeper"]


def test_plan_bundle_and_plan_strategies() -> None:
    bundle = load_plan_bundle(resolve_latest_plan_version())
    assert "default" in bundle.plans
    assert PlanStrategies.get_plan_by_name("bold")["name"] == "bold"
    assert PlanStrategies.default_role_style_plan_names("wolf") == [
        "wolf_conservative",
        "wolf_aggressive",
        "wolf_skeptical",
        "wolf_coordinator",
    ]
    plan = PlanStrategies.get_plan_by_name("wolf_skeptical")
    assert "狼人质疑派打法" in plan["wolf"]
