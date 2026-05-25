from llm_werewolf.agent_team.memory.procedural_memory import ProceduralMemory


def test_procedural_memory_exposes_role_rules_and_plans():
    memory = ProceduralMemory()

    rules = memory.get_role_rules("villager")
    plan_text = memory.get_plan_text("bold", "villager")
    summary = memory.build_plan_summary("bold", "villager")

    assert "role_instruction" in rules
    assert plan_text == "大胆发言"
    assert "角色固定职责" in summary
    assert "当前采用计划：bold" in summary
