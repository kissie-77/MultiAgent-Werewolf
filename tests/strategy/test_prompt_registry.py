"""Per-role prompt package schema tests (replaces legacy v2 bundle registry tests)."""

from llm_werewolf.strategy.registry.prompt_yaml_utils import coerce_text_dict, coerce_text_list
from llm_werewolf.strategy.registry.role_prompt_registry import (
    agent_base_template_path,
    build_role_strategy_prompt,
    get_role_card,
    resolve_latest_prompt_version,
)
from llm_werewolf.game_runtime.prompts.manager import PromptManager


def test_agent_base_loaded_from_shared_template() -> None:
    text = agent_base_template_path().read_text(encoding="utf-8")
    assert "多 Agent 狼人杀博弈" in text
    assert "{number}" in text
    assert "{role_name}" in text


def test_per_role_card() -> None:
    wolf = get_role_card("wolf", resolve_latest_prompt_version("wolf"))
    assert wolf["role_name"] == "狼人"
    assert "狼人阵营" in wolf["role_instruction"]


def test_build_role_strategy_prompt() -> None:
    version = resolve_latest_prompt_version("wolf")
    wolf = get_role_card("wolf", version)
    prompt = build_role_strategy_prompt(3, "wolf", "测试计划", prompt_version=version)
    assert "你的座位号是：3" in prompt
    assert "测试计划" in prompt


def test_extended_role_cards() -> None:
    white_wolf = get_role_card("white_wolf", resolve_latest_prompt_version("white_wolf"))
    cupid = get_role_card("cupid", resolve_latest_prompt_version("cupid"))
    assert white_wolf["role_name"] == "白狼"
    assert cupid["role_name"] == "丘比特"


def test_prompt_manager_uses_extended_role_specific_keys() -> None:
    assert PromptManager.get_prompt_role_key("White Wolf") == "white_wolf"
    assert PromptManager.get_prompt_role_key("Cupid") == "cupid"
    assert PromptManager.get_prompt_role_key("Graveyard Keeper") == "graveyard_keeper"


def test_role_card_exposes_structured_compatibility_fields() -> None:
    villager = get_role_card("villager", resolve_latest_prompt_version("villager"))
    assert "长期规则：" in villager["suggestion"]
    assert "阶段策略：" in villager["suggestion"]
    assert "禁止项：" in villager["suggestion"]
    assert "不靠身份想象做判断" in villager["core_principles"]
    assert "opening:" in villager["phase_strategies"]
    assert "禁止最后一分钟无理由跳票" in villager["forbidden_actions"]


def test_structured_role_card_renders_into_agent_prompt() -> None:
    version = resolve_latest_prompt_version("villager")
    villager = get_role_card("villager", version)
    prompt = build_role_strategy_prompt(
        5,
        "villager",
        "测试计划",
        prompt_version=version,
    )
    assert "长期规则：" in prompt
    assert "禁止项：" in prompt


def test_all_22_roles_have_structured_fields() -> None:
    role_keys = [
        "villager", "prophet", "witch", "wolf", "wolf_king", "guard", "hunter",
        "white_wolf", "wolf_beauty", "guardian_wolf", "hidden_wolf", "nightmare_wolf",
        "blood_moon_apostle", "idiot", "elder", "knight", "magician", "cupid",
        "raven", "graveyard_keeper", "thief", "lover",
    ]
    for key in role_keys:
        version = resolve_latest_prompt_version(key)
        card = get_role_card(key, version)
        assert card["role_name"], f"{key}: role_name is empty"
        assert card["role_instruction"], f"{key}: role_instruction is empty"
        assert card["core_principles"], f"{key}: core_principles is empty"
        assert card["phase_strategies"], f"{key}: phase_strategies is empty"
        assert card["forbidden_actions"], f"{key}: forbidden_actions is empty"
        assert card["examples"], f"{key}: examples is empty"
        assert "长期规则：" in card["suggestion"], f"{key}: suggestion missing 长期规则"
        assert "阶段策略：" in card["suggestion"], f"{key}: suggestion missing 阶段策略"
        assert "禁止项：" in card["suggestion"], f"{key}: suggestion missing 禁止项"


def test_structured_fields_have_correct_types() -> None:
    wolf = get_role_card("wolf", resolve_latest_prompt_version("wolf"))
    assert isinstance(wolf["core_principles"], str)
    assert len(wolf["core_principles"].split("\n")) >= 3
    assert isinstance(wolf["phase_strategies"], str)
    assert "opening:" in wolf["phase_strategies"]
    assert isinstance(wolf["forbidden_actions"], str)
    assert len(wolf["forbidden_actions"].split("\n")) >= 3
    assert isinstance(wolf["examples"], str)
    assert len(wolf["examples"].split("\n")) >= 2


def test_prompt_manager_builds_prompt_for_all_extended_roles() -> None:
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
    assert coerce_text_list(None) == []
    assert coerce_text_list("") == []
    assert coerce_text_list("single") == ["single"]
    assert coerce_text_list(["a", "b", "c"]) == ["a", "b", "c"]
    assert coerce_text_list(["a", "", "b"]) == ["a", "b"]
    assert coerce_text_list(123) == ["123"]


def test_coerce_text_dict_handles_edge_cases() -> None:
    assert coerce_text_dict(None) == {}
    assert coerce_text_dict("not a dict") == {}
    assert coerce_text_dict({"a": "1", "b": "2"}) == {"a": "1", "b": "2"}
    assert coerce_text_dict({"a": "", "b": "2"}) == {"b": "2"}
