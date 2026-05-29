"""声明式角色目录的测试。"""

from llm_werewolf.game_runtime.roles import Seer, Werewolf
from llm_werewolf.game_runtime.types.enums import Camp, VictoryGoal
from llm_werewolf.game_runtime.roles.loader import role_class_from_definition
from llm_werewolf.game_runtime.roles.catalog import (
    get_catalog,
    get_definition,
    get_definition_by_role_class,
)
from llm_werewolf.game_runtime.registries.role_registry import (
    create_roles,
    get_role_map,
    get_werewolf_roles,
)


def test_catalog_has_four_fields() -> None:
    seer = get_definition("Seer")
    assert seer.name == "Seer"
    assert seer.display_name == "预言家"
    assert "villager:Seer" in seer.implementation
    assert seer.camp == Camp.VILLAGER
    assert seer.victory_goal == VictoryGoal.VILLAGER_ELIMINATE_WEREWOLVES


def test_role_class_resolution() -> None:
    definition = get_definition("Werewolf")
    assert role_class_from_definition(definition) is Werewolf


def test_registry_matches_catalog() -> None:
    catalog_names = {d.name for d in get_catalog()}
    assert catalog_names == set(get_role_map().keys())


def test_werewolf_roles_from_camp() -> None:
    wolves = get_werewolf_roles()
    assert "Werewolf" in wolves
    assert "Seer" not in wolves


def test_create_roles_from_names() -> None:
    roles = create_roles(["Seer", "Werewolf", "Villager", "Witch", "Hunter", "Guard"])
    assert roles[0] is Seer


def test_definition_by_role_class() -> None:
    definition = get_definition_by_role_class(Seer)
    assert definition.display_name == "预言家"
