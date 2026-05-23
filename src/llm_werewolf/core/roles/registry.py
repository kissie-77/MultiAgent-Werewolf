"""Role registry backed by declarative role catalog."""

from __future__ import annotations

from llm_werewolf.core.roles.base import Role
from llm_werewolf.core.roles.catalog import ROLE_CATALOG, get_definition
from llm_werewolf.core.roles.definition import RoleDefinition
from llm_werewolf.core.roles.loader import role_class_from_definition
from llm_werewolf.core.types.enums import Camp


class _ConfigProbe:
    """Minimal player stand-in to read Role.config.name without a full game."""

    player_id = "_probe"

    def is_alive(self) -> bool:
        return True


def get_role_map() -> dict[str, type[Role]]:
    """Map registry name -> Role class (from definition implementation paths)."""
    return {d.name: role_class_from_definition(d) for d in ROLE_CATALOG}


def runtime_role_name(catalog_name: str) -> str:
    """Map catalog registry name (e.g. AlphaWolf) to Role.config.name (e.g. Alpha Wolf)."""
    role_cls = get_role_map()[catalog_name]
    return role_cls(_ConfigProbe()).name  # type: ignore[arg-type]


def build_catalog_to_runtime_map() -> dict[str, str]:
    return {d.name: runtime_role_name(d.name) for d in ROLE_CATALOG}


CATALOG_TO_RUNTIME_NAME: dict[str, str] = build_catalog_to_runtime_map()


def get_role_definitions() -> list[RoleDefinition]:
    """Return all registered role definitions."""
    return list(ROLE_CATALOG)


def get_role_definition(name: str) -> RoleDefinition:
    """Get definition by registry name."""
    return get_definition(name)


def get_werewolf_roles() -> set[str]:
    """Runtime role names (Role.config.name) for werewolf-camp roles."""
    return {
        CATALOG_TO_RUNTIME_NAME[d.name]
        for d in ROLE_CATALOG
        if d.camp == Camp.WEREWOLF
    }


def validate_role_names(role_names: list[str]) -> None:
    """Validate role names and ensure at least one werewolf."""
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
    """Create Role class list from registry names."""
    role_map = get_role_map()
    roles: list[type[Role]] = []

    for role_name in role_names:
        if role_name not in role_map:
            msg = f"Unknown role: {role_name}"
            raise ValueError(msg)
        roles.append(role_map[role_name])

    return roles
