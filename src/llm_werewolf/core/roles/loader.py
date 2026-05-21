"""Load role classes from definition implementation paths."""

import importlib
from typing import TypeVar

from llm_werewolf.core.roles.base import Role
from llm_werewolf.core.roles.definition import RoleDefinition

T = TypeVar("T", bound=type[Role])


def import_role_class(implementation: str) -> type[Role]:
    """Import a role class from ``module.path:ClassName``."""
    if ":" not in implementation:
        msg = f"Invalid implementation path '{implementation}', expected format 'module:Class'"
        raise ValueError(msg)
    module_name, class_name = implementation.split(":", 1)
    module = importlib.import_module(module_name)
    role_class = getattr(module, class_name)
    if not isinstance(role_class, type) or not issubclass(role_class, Role):
        msg = f"Implementation '{implementation}' is not a Role subclass"
        raise TypeError(msg)
    return role_class


def role_class_from_definition(definition: RoleDefinition) -> type[Role]:
    """Resolve the Role class for a role definition."""
    return import_role_class(definition.implementation)
