"""Role registry backed by declarative role catalog."""

from llm_werewolf.core.roles.base import Role
from llm_werewolf.core.roles.catalog import ROLE_CATALOG, get_definition
from llm_werewolf.core.roles.definition import RoleDefinition
from llm_werewolf.core.roles.loader import role_class_from_definition
from llm_werewolf.core.types.enums import Camp


def get_role_definitions() -> list[RoleDefinition]:
    """Return all registered role definitions."""
    return list(ROLE_CATALOG)


def get_role_map() -> dict[str, type[Role]]:
    """Map registry name -> Role class (from definition implementation paths)."""
    return {d.name: role_class_from_definition(d) for d in ROLE_CATALOG}


def get_role_definition(name: str) -> RoleDefinition:
    """Get definition by registry name."""
    return get_definition(name)


def get_werewolf_roles() -> set[str]:
    """Role names that belong to the werewolf camp."""
    return {d.name for d in ROLE_CATALOG if d.camp == Camp.WEREWOLF}


def validate_role_names(role_names: list[str]) -> None:
    """Validate role names and ensure at least one werewolf."""
    role_map = get_role_map()
    werewolf_roles = get_werewolf_roles()

    for role_name in role_names:
        if role_name not in role_map:
            msg = f"Unknown role: {role_name}"
            raise ValueError(msg)

    werewolf_count = sum(1 for role in role_names if role in werewolf_roles)
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
