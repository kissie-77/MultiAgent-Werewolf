"""Per-role prompt package tests."""

from llm_werewolf.strategy.role_prompt_registry import build_role_strategy_prompt, get_role_card
from llm_werewolf.strategy.role_version_manifest import RoleVersionManifest, set_active_manifest


def test_v1_wolf_role_package() -> None:
    wolf = get_role_card("wolf", "v1")
    assert wolf["role_name"] == "狼人"
    assert "狼人阵营" in wolf["role_instruction"]


def test_build_role_strategy_prompt_v1() -> None:
    set_active_manifest(RoleVersionManifest())
    prompt = build_role_strategy_prompt(3, "wolf", "测试计划", prompt_version="v1")
    assert "你的座位号是：3" in prompt
    assert "测试计划" in prompt
    assert "长期规则：" in prompt
