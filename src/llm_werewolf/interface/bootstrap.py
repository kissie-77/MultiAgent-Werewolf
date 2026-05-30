"""Backward-compatible re-export of CLI runtime bootstrap helpers."""

from llm_werewolf.interface.cli.runtime.bootstrap import (
    bind_agentscope_roles,
    create_information_hub,
    create_players_from_config,
    prepare_game_roster,
    wire_agentscope_after_setup,
)

__all__ = [
    "bind_agentscope_roles",
    "create_information_hub",
    "create_players_from_config",
    "prepare_game_roster",
    "wire_agentscope_after_setup",
]
