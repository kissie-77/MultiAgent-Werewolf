"""Runtime construction helpers for the Textual TUI entrypoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.interface.modes import resolve_config_path
from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.interface.bootstrap import prepare_game_roster, wire_agentscope_after_setup
from llm_werewolf.interface.player_roster import resolve_participation

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.game_runtime.config import PlayersConfig


@dataclass(frozen=True)
class TUIRunSettings:
    """Startup defaults selected by CLI arguments or the TUI setup screen."""

    config: str | None = None
    participation: str = "all_agent"
    rules: str = "badge_flow"
    num_players: int | None = None
    enable_sheriff: bool | None = None
    show_agent_raw: bool = False


@dataclass(frozen=True)
class TUIRuntime:
    """Concrete game runtime created from TUI settings."""

    engine: GameEngine
    players_config: PlayersConfig
    config_path: Path
    participation: str
    num_players: int


def create_tui_runtime(settings: TUIRunSettings) -> TUIRuntime:
    """Create and setup a GameEngine for the TUI."""
    config_path = resolve_config_path(
        settings.config,
        participation=settings.participation,
        rules=settings.rules,
    )
    players_config = load_config(config_path=config_path)
    effective_participation = resolve_participation(
        players_config,
        requested_participation=settings.participation,
    )

    players, roles, game_config = prepare_game_roster(
        players_config,
        num_players=settings.num_players,
        enable_sheriff=settings.enable_sheriff,
    )

    engine = GameEngine(game_config, language=players_config.language)
    engine.setup_game(players=players, roles=roles)
    wire_agentscope_after_setup(
        engine,
        players_config,
        show_agent_raw=settings.show_agent_raw,
    )

    return TUIRuntime(
        engine=engine,
        players_config=players_config,
        config_path=config_path,
        participation=effective_participation,
        num_players=game_config.num_players,
    )
