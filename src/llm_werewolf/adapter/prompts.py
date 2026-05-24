"""Compatibility exports for strategy role prompts.

The canonical role strategy prompts live in
``llm_werewolf.strategy.role_prompts``.  This module keeps older imports from
``llm_werewolf.adapter.prompts`` working during the architecture migration.
"""

from llm_werewolf.strategy.role_prompts import (
    GamePrompts,
    PlanStrategies,
    ROLE_SEAT_ACTION,
    RolePrompts,
    build_role_seat_action_map,
)

__all__ = [
    "GamePrompts",
    "PlanStrategies",
    "ROLE_SEAT_ACTION",
    "RolePrompts",
    "build_role_seat_action_map",
]
