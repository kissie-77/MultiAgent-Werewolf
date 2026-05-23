"""向后兼容的重导出；请优先使用 ``llm_werewolf.core.roles.registry``。"""

from llm_werewolf.core.roles.registry import (
    create_roles,
    get_role_definitions,
    get_role_map,
    get_werewolf_roles,
    validate_role_names,
)


def get_role_class(name: str) -> type:
    """按注册表名称返回角色类。"""
    return get_role_map()[name]


def list_roles() -> list[str]:
    """返回所有已注册的角色名称。"""
    return list(get_role_map().keys())


__all__ = [
    "create_roles",
    "get_role_class",
    "get_role_definitions",
    "get_role_map",
    "get_werewolf_roles",
    "list_roles",
    "validate_role_names",
]
