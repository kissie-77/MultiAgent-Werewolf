"""CLI runtime helpers: roster wiring, modes, seat overrides."""

from llm_werewolf.interface.cli.runtime.modes import GameMode, list_modes, resolve_config_path
from llm_werewolf.interface.cli.runtime.bootstrap import (
    prepare_game_roster,
    bind_agentscope_roles,
    create_information_hub,
    create_players_from_config,
    wire_agentscope_after_setup,
)
from llm_werewolf.interface.cli.runtime.overrides import parse_seat_list, apply_human_seats
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


def __getattr__(name: str):
    if name == "finalize_run":
        from llm_werewolf.interface.cli.runtime.finalize_run import finalize_run

        return finalize_run
    if name == "persist_run_artifacts":
        from llm_werewolf.interface.cli.runtime.finalize_run import persist_run_artifacts

        return persist_run_artifacts
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
