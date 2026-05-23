from pathlib import Path

import fire
import logfire

from llm_werewolf.core.env import load_project_dotenv

load_project_dotenv()

from llm_werewolf.adapter.bootstrap import (
    prepare_game_roster,
    wire_agentscope_after_setup,
)
from llm_werewolf.ui import run_tui
from llm_werewolf.core import GameEngine
from llm_werewolf.core.utils import load_config


def main(config: str) -> None:
    """Run Werewolf game with TUI interface.

    Args:
        config: Path to the YAML configuration file
    """
    config_path = Path(config)
    players_config = load_config(config_path=config_path)

    num_players = len(players_config.players)
    players, roles, game_config = prepare_game_roster(players_config)

    engine = GameEngine(game_config, language=players_config.language)
    engine.setup_game(players=players, roles=roles)
    wire_agentscope_after_setup(engine, players_config)

    logfire.info("tui_started", config_path=str(config_path), num_players=num_players)

    try:
        run_tui(engine)
    except KeyboardInterrupt:
        logfire.info("tui_aborted_by_user", config_path=str(config_path), num_players=num_players)
    except Exception as exc:
        logfire.error(
            "tui_execution_error",
            error=str(exc),
            config_path=str(config_path),
            num_players=num_players,
        )
        raise


def entry() -> None:
    """Entry point for the werewolf TUI command."""
    fire.Fire(main)


if __name__ == "__main__":
    entry()
