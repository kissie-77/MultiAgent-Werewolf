"""Prompt 注册表：per-role / phase / plan 加载与版本管理。"""

from llm_werewolf.strategy.registry.role_prompts import (
    ROLE_SEAT_ACTION,
    GamePrompts,
    RolePrompts,
    PlanStrategies,
)
from llm_werewolf.strategy.registry.role_prompt_registry import (
    get_role_card,
    list_prompt_versions,
    build_role_strategy_prompt,
)
from llm_werewolf.strategy.registry.role_version_manifest import (
    RoleVersionManifest,
    version_sort_key,
    get_active_manifest,
    pick_latest_version,
    set_active_manifest,
)

__all__ = [
    "ROLE_SEAT_ACTION",
    "GamePrompts",
    "PlanStrategies",
    "RolePrompts",
    "RoleVersionManifest",
    "build_role_strategy_prompt",
    "get_active_manifest",
    "get_role_card",
    "list_prompt_versions",
    "pick_latest_version",
    "set_active_manifest",
    "version_sort_key",
]
