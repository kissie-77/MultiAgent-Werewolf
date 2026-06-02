"""Prompt 变量 registry。"""

from llm_werewolf.strategy.prompt_registry import get_registry, role_prompt_key_to_variable
from llm_werewolf.game_runtime.prompts.manager import PromptManager


def test_v2_agent_base_loaded() -> None:
    registry = get_registry("v2")
    text = registry.get_text("v2.agent.base")
    assert "多 Agent 狼人杀博弈" in text
    assert "{number}" in text
    assert "{role_name}" in text
    assert "不要推断、讨论或利用任何玩家的游戏外控制方式、运行环境或技术来源" in text


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


def test_extended_role_cards_are_registered() -> None:
    registry = get_registry("v2")
    white_wolf = registry.get_role_card("v2.role.white_wolf")
    cupid = registry.get_role_card("v2.role.cupid")
    assert white_wolf["role_name"] == "白狼"
    assert "中后盘" in white_wolf["suggestion"]
    assert cupid["role_name"] == "丘比特"
    assert "首夜" in cupid["suggestion"]


def test_prompt_manager_uses_extended_role_specific_keys() -> None:
    assert PromptManager.get_prompt_role_key("White Wolf") == "white_wolf"
    assert PromptManager.get_prompt_role_key("Cupid") == "cupid"
    assert PromptManager.get_prompt_role_key("Graveyard Keeper") == "graveyard_keeper"


def test_role_card_exposes_structured_compatibility_fields() -> None:
    registry = get_registry("v2")
    villager = registry.get_role_card("v2.role.villager")
    assert "长期规则：" in villager["suggestion"]
    assert "阶段策略：" in villager["suggestion"]
    assert "禁止项：" in villager["suggestion"]
    assert "不靠身份想象做判断" in villager["core_principles"]
    assert "opening:" in villager["phase_strategies"]
    assert "禁止最后一分钟无理由跳票" in villager["forbidden_actions"]


def test_structured_role_card_still_renders_into_agent_prompt() -> None:
    registry = get_registry("v2")
    villager = registry.get_role_card("v2.role.villager")
    prompt = registry.resolve(
        "v2.agent.base",
        number=5,
        role_name=villager["role_name"],
        role_instruction=villager["role_instruction"],
        suggestion=villager["suggestion"],
        plan="测试计划",
    )
    assert "长期规则：" in prompt
    assert "禁止项：" in prompt


def test_all_22_roles_have_structured_fields() -> None:
    """所有 22 个角色都应该有新 schema 的结构化字段。"""
    registry = get_registry("v2")
    role_keys = [
        "villager", "prophet", "witch", "wolf", "wolf_king", "guard", "hunter",
        "white_wolf", "wolf_beauty", "guardian_wolf", "hidden_wolf", "nightmare_wolf",
        "blood_moon_apostle", "idiot", "elder", "knight", "magician", "cupid",
        "raven", "graveyard_keeper", "thief", "lover",
    ]
    for key in role_keys:
        card = registry.get_role_card(f"v2.role.{key}")
        assert card["role_name"], f"{key}: role_name is empty"
        assert card["role_instruction"], f"{key}: role_instruction is empty"
        assert card["core_principles"], f"{key}: core_principles is empty"
        assert card["phase_strategies"], f"{key}: phase_strategies is empty"
        assert card["forbidden_actions"], f"{key}: forbidden_actions is empty"
        assert card["examples"], f"{key}: examples is empty"
        # suggestion 应该由 _render_legacy_suggestion 生成
        assert "长期规则：" in card["suggestion"], f"{key}: suggestion missing 长期规则"
        assert "阶段策略：" in card["suggestion"], f"{key}: suggestion missing 阶段策略"
        assert "禁止项：" in card["suggestion"], f"{key}: suggestion missing 禁止项"


def test_structured_fields_have_correct_types() -> None:
    """结构化字段应该有正确的类型。"""
    from llm_werewolf.strategy.prompt_registry import _coerce_text_list, _coerce_text_dict

    registry = get_registry("v2")
    wolf = registry.get_role_card("v2.role.wolf")

    # core_principles 应该是换行分隔的字符串
    assert isinstance(wolf["core_principles"], str)
    assert len(wolf["core_principles"].split("\n")) >= 3

    # phase_strategies 应该是换行分隔的字符串，每行格式为 "key: value"
    assert isinstance(wolf["phase_strategies"], str)
    assert "opening:" in wolf["phase_strategies"]

    # forbidden_actions 应该是换行分隔的字符串
    assert isinstance(wolf["forbidden_actions"], str)
    assert len(wolf["forbidden_actions"].split("\n")) >= 3

    # examples 应该是换行分隔的字符串
    assert isinstance(wolf["examples"], str)
    assert len(wolf["examples"].split("\n")) >= 2


def test_prompt_manager_builds_prompt_for_all_extended_roles() -> None:
    """PromptManager 应该能为所有 22 个角色构建 prompt。"""
    from llm_werewolf.game_runtime.prompts.manager import PromptManager

    extended_roles = [
        "White Wolf", "Wolf Beauty", "Guardian Wolf", "Hidden Wolf",
        "Nightmare Wolf", "Blood Moon Apostle", "Idiot", "Elder",
        "Knight", "Cupid", "Raven", "Magician", "Graveyard Keeper",
        "Thief", "Lover",
    ]
    for role_name in extended_roles:
        key = PromptManager.get_prompt_role_key(role_name)
        prompt = PromptManager.build_prompt_key_strategy_prompt(
            seat_number=1, prompt_role_key=key, plan_text="测试", prompt_version="v1"
        )
        assert prompt, f"{role_name}: prompt is empty"
        assert "长期规则：" in prompt, f"{role_name}: prompt missing structured content"


def test_coerce_text_list_handles_edge_cases() -> None:
    """_coerce_text_list 应该正确处理各种边界情况。"""
    from llm_werewolf.strategy.prompt_registry import _coerce_text_list

    assert _coerce_text_list(None) == []
    assert _coerce_text_list("") == []
    assert _coerce_text_list("single") == ["single"]
    assert _coerce_text_list(["a", "b", "c"]) == ["a", "b", "c"]
    assert _coerce_text_list(["a", "", "b"]) == ["a", "b"]
    assert _coerce_text_list(123) == ["123"]


def test_coerce_text_dict_handles_edge_cases() -> None:
    """_coerce_text_dict 应该正确处理各种边界情况。"""
    from llm_werewolf.strategy.prompt_registry import _coerce_text_dict

    assert _coerce_text_dict(None) == {}
    assert _coerce_text_dict("not a dict") == {}
    assert _coerce_text_dict({"a": "1", "b": "2"}) == {"a": "1", "b": "2"}
    assert _coerce_text_dict({"a": "", "b": "2"}) == {"b": "2"}
