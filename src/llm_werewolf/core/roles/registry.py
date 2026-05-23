"""基于声明式角色目录的角色注册表。"""

from __future__ import annotations

from llm_werewolf.core.roles.base import Role
from llm_werewolf.core.roles.catalog import ROLE_CATALOG, get_definition
from llm_werewolf.core.roles.definition import RoleDefinition
from llm_werewolf.core.roles.loader import role_class_from_definition
from llm_werewolf.core.types.enums import Camp


class _ConfigProbe:
    """用于在无完整对局时读取 Role.config.name 的最小玩家占位。"""

    player_id = "_probe"

    def is_alive(self) -> bool:
        return True


def get_role_map() -> dict[str, type[Role]]:
    """映射注册表名称 -> 角色类（来自定义中的实现路径）。"""
    return {d.name: role_class_from_definition(d) for d in ROLE_CATALOG}


def runtime_role_name(catalog_name: str) -> str:
    """将目录注册名（如 AlphaWolf）映射为 Role.config.name（如 Alpha Wolf）。"""
    role_cls = get_role_map()[catalog_name]
    return role_cls(_ConfigProbe()).name  # type: ignore[arg-type]


def build_catalog_to_runtime_map() -> dict[str, str]:
    return {d.name: runtime_role_name(d.name) for d in ROLE_CATALOG}


CATALOG_TO_RUNTIME_NAME: dict[str, str] = build_catalog_to_runtime_map()


def get_role_definitions() -> list[RoleDefinition]:
    """返回所有已注册的角色定义。"""
    return list(ROLE_CATALOG)


def get_role_definition(name: str) -> RoleDefinition:
    """按注册表名称获取定义。"""
    return get_definition(name)


def get_werewolf_roles() -> set[str]:
    """狼人阵营的运行时角色名（Role.config.name）集合。"""
    return {
        CATALOG_TO_RUNTIME_NAME[d.name]
        for d in ROLE_CATALOG
        if d.camp == Camp.WEREWOLF
    }


def validate_role_names(role_names: list[str]) -> None:
    """校验角色名称并确保至少有一名狼人。"""
    role_map = get_role_map()

    for role_name in role_names:
        if role_name not in role_map:
            msg = f"Unknown role: {role_name}"
            raise ValueError(msg)

    werewolf_count = sum(
        1 for role in role_names if get_definition(role).camp == Camp.WEREWOLF
    )
    if werewolf_count == 0:
        msg = "At least one werewolf role is required"
        raise ValueError(msg)


def create_roles(role_names: list[str]) -> list[type[Role]]:
    """根据注册表名称列表创建角色类列表。"""
    role_map = get_role_map()
    roles: list[type[Role]] = []

    for role_name in role_names:
        if role_name not in role_map:
            msg = f"Unknown role: {role_name}"
            raise ValueError(msg)
        roles.append(role_map[role_name])

    return roles
