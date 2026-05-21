"""Backward-compatible re-export; prefer ``llm_werewolf.core.roles.registry``."""

from llm_werewolf.core.roles.registry import (
    create_roles,
    get_role_definitions,
    get_role_map,
    get_werewolf_roles,
    validate_role_names,
)


def get_role_class(name: str) -> type:
    """Return role class by registry name."""
    return get_role_map()[name]


def list_roles() -> list[str]:
    """Return all registered role names."""
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
