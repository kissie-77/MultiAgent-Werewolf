"""Prompt 变量 registry。"""

from llm_werewolf.strategy.prompt_registry import get_registry, role_prompt_key_to_variable


def test_v2_agent_base_loaded() -> None:
    registry = get_registry("v2")
    text = registry.get_text("v2.agent.base")
    assert "多 Agent 狼人杀博弈" in text
    assert "{number}" in text
    assert "{role_name}" in text


def test_v2_role_card() -> None:
    registry = get_registry("v2")
    wolf = registry.get_role_card("v2.role.wolf")
    assert wolf["role_name"] == "狼人"
    assert "狼人阵营" in wolf["role_instruction"]


def test_resolve_agent_prompt() -> None:
    registry = get_registry("v2")
    wolf = registry.get_role_card("v2.role.wolf")
    prompt = registry.resolve(
        "v2.agent.base",
        number=3,
        role_name=wolf["role_name"],
        role_instruction=wolf["role_instruction"],
        suggestion=wolf["suggestion"],
        plan="测试计划",
    )
    assert "你的座位号是：3" in prompt
    assert "测试计划" in prompt


def test_role_key_variable_mapping() -> None:
    assert role_prompt_key_to_variable("wolf") == "v2.role.wolf"
