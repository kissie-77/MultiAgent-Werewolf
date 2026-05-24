"""game_runtime/role_registry.py 模块的测试。"""

import pytest

from llm_werewolf.game_runtime.roles import Seer, Witch, Villager, Werewolf, AlphaWolf, WhiteWolf
from llm_werewolf.game_runtime.roles.base import Role
from llm_werewolf.game_runtime.roles.registry import (
    create_roles,
    get_role_map,
    get_werewolf_roles,
    validate_role_names,
)


class TestGetRoleMap:
    """get_role_map 函数的测试。"""

    def test_get_role_map_returns_dict(self) -> None:
        """测试 get_role_map 返回字典。"""
        role_map = get_role_map()
        assert isinstance(role_map, dict)

    def test_get_role_map_contains_werewolf(self) -> None:
        """测试角色映射包含 Werewolf。"""
        role_map = get_role_map()
        assert "Werewolf" in role_map
        assert role_map["Werewolf"] == Werewolf

    def test_get_role_map_contains_villager_roles(self) -> None:
        """测试角色映射包含村民阵营角色。"""
        role_map = get_role_map()
        assert "Villager" in role_map
        assert "Seer" in role_map
        assert "Witch" in role_map
        assert "Hunter" in role_map
        assert "Guard" in role_map

    def test_get_role_map_contains_special_werewolves(self) -> None:
        """测试角色映射包含特殊狼人角色。"""
        role_map = get_role_map()
        assert "AlphaWolf" in role_map
        assert "WhiteWolf" in role_map
        assert "WolfBeauty" in role_map
        assert "HiddenWolf" in role_map

    def test_get_role_map_all_values_are_role_classes(self) -> None:
        """测试角色映射中所有值均为 Role 类。"""
        role_map = get_role_map()
        for role_class in role_map.values():
            assert issubclass(role_class, Role)


class TestGetWerewolfRoles:
    """get_werewolf_roles 函数的测试。"""

    def test_get_werewolf_roles_returns_set(self) -> None:
        """测试 get_werewolf_roles 返回集合。"""
        werewolf_roles = get_werewolf_roles()
        assert isinstance(werewolf_roles, set)

    def test_get_werewolf_roles_contains_werewolf(self) -> None:
        """测试狼人角色集合包含 Werewolf。"""
        werewolf_roles = get_werewolf_roles()
        assert "Werewolf" in werewolf_roles

    def test_get_werewolf_roles_contains_special_werewolves(self) -> None:
        """测试狼人角色集合包含特殊狼人。"""
        werewolf_roles = get_werewolf_roles()
        assert "Alpha Wolf" in werewolf_roles
        assert "White Wolf" in werewolf_roles
        assert "Wolf Beauty" in werewolf_roles
        assert "Hidden Wolf" in werewolf_roles

    def test_get_werewolf_roles_not_contains_villager(self) -> None:
        """测试狼人角色集合不包含村民阵营角色。"""
        werewolf_roles = get_werewolf_roles()
        assert "Villager" not in werewolf_roles
        assert "Seer" not in werewolf_roles
        assert "Witch" not in werewolf_roles


class TestValidateRoleNames:
    """validate_role_names 函数的测试。"""

    def test_validate_valid_role_names(self) -> None:
        """测试验证有效角色名。"""
        role_names = ["Werewolf", "Werewolf", "Villager", "Seer", "Witch"]
        # 不应抛出任何异常
        validate_role_names(role_names)

    def test_validate_with_special_werewolves(self) -> None:
        """测试验证含特殊狼人角色。"""
        role_names = ["AlphaWolf", "WhiteWolf", "Villager", "Seer"]
        # 不应抛出任何异常
        validate_role_names(role_names)

    def test_validate_unknown_role_raises_error(self) -> None:
        """测试未知角色抛出 ValueError。"""
        role_names = ["Werewolf", "UnknownRole", "Villager"]
        with pytest.raises(ValueError, match="Unknown role: UnknownRole"):
            validate_role_names(role_names)

    def test_validate_no_werewolf_raises_error(self) -> None:
        """测试无狼人时抛出 ValueError。"""
        role_names = ["Villager", "Seer", "Witch", "Hunter"]
        with pytest.raises(ValueError, match="At least one werewolf role is required"):
            validate_role_names(role_names)

    def test_validate_empty_list_raises_error(self) -> None:
        """测试空列表抛出 ValueError。"""
        role_names: list[str] = []
        with pytest.raises(ValueError, match="At least one werewolf role is required"):
            validate_role_names(role_names)

    def test_validate_single_werewolf(self) -> None:
        """测试单个狼人有效。"""
        role_names = ["Werewolf"]
        # 不应抛出任何异常
        validate_role_names(role_names)


class TestCreateRoles:
    """create_roles 函数的测试。"""

    def test_create_roles_returns_list(self) -> None:
        """测试 create_roles 返回列表。"""
        role_names = ["Werewolf", "Villager"]
        roles = create_roles(role_names)
        assert isinstance(roles, list)
        assert len(roles) == 2

    def test_create_roles_basic_roles(self) -> None:
        """测试创建基础角色。"""
        role_names = ["Werewolf", "Villager", "Seer"]
        roles = create_roles(role_names)

        assert len(roles) == 3
        assert roles[0] == Werewolf
        assert roles[1] == Villager
        assert roles[2] == Seer

    def test_create_roles_special_werewolves(self) -> None:
        """测试创建特殊狼人角色。"""
        role_names = ["AlphaWolf", "WhiteWolf"]
        roles = create_roles(role_names)

        assert len(roles) == 2
        assert roles[0] == AlphaWolf
        assert roles[1] == WhiteWolf

    def test_create_roles_unknown_role_raises_error(self) -> None:
        """测试未知角色抛出 ValueError。"""
        role_names = ["Werewolf", "InvalidRole"]
        with pytest.raises(ValueError, match="Unknown role: InvalidRole"):
            create_roles(role_names)

    def test_create_roles_preserves_order(self) -> None:
        """测试 create_roles 保持顺序。"""
        role_names = ["Seer", "Werewolf", "Witch", "Villager"]
        roles = create_roles(role_names)

        assert len(roles) == 4
        assert roles[0] == Seer
        assert roles[1] == Werewolf
        assert roles[2] == Witch
        assert roles[3] == Villager

    def test_create_roles_allows_duplicates(self) -> None:
        """测试 create_roles 允许重复角色名。"""
        role_names = ["Werewolf", "Werewolf", "Villager", "Villager", "Villager"]
        roles = create_roles(role_names)

        assert len(roles) == 5
        assert roles[0] == Werewolf
        assert roles[1] == Werewolf
        assert roles[2] == Villager
        assert roles[3] == Villager
        assert roles[4] == Villager

    def test_create_roles_empty_list(self) -> None:
        """测试从空列表创建角色。"""
        role_names: list[str] = []
        roles = create_roles(role_names)
        assert len(roles) == 0

    def test_create_roles_returns_role_classes(self) -> None:
        """测试 create_roles 返回 Role 类。"""
        role_names = ["Werewolf", "Villager"]
        roles = create_roles(role_names)

        for role_class in roles:
            assert issubclass(role_class, Role)
