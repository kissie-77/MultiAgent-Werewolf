"""CLI runtime helpers: roster wiring, modes, seat overrides."""

from llm_werewolf.interface.cli.runtime.bootstrap import (
    bind_agentscope_roles,
    create_information_hub,
    create_players_from_config,
    prepare_game_roster,
    wire_agentscope_after_setup,
)
from llm_werewolf.interface.cli.runtime.finalize_run import finalize_run, persist_run_artifacts
from llm_werewolf.interface.cli.runtime.modes import GameMode, list_modes, resolve_config_path
from llm_werewolf.interface.cli.runtime.overrides import apply_human_seats, parse_seat_list
from llm_werewolf.interface.cli.runtime.player_count import resize_players_config

__all__ = [
    "GameMode",
    "apply_human_seats",
    "bind_agentscope_roles",
    "create_information_hub",
    "create_players_from_config",
    "finalize_run",
    "list_modes",
    "parse_seat_list",
    "persist_run_artifacts",
    "prepare_game_roster",
    "resize_players_config",
    "resolve_config_path",
    "wire_agentscope_after_setup",
]
