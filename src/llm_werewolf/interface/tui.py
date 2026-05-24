import fire
import logfire

from llm_werewolf.game_runtime.env import load_project_dotenv

load_project_dotenv()

from llm_werewolf.interface.bootstrap import (
    prepare_game_roster,
    wire_agentscope_after_setup,
)
from llm_werewolf.ui import run_tui
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.interface.modes import resolve_config_path


def main(
    config: str | None = None,
    participation: str = "all_agent",
    rules: str = "badge_flow",
) -> None:
    """使用 TUI 界面运行狼人杀游戏。

    Args:
        config: YAML 配置文件路径；提供后优先于模式选择。
        participation: 参与方式，例如 all_agent。
        rules: 规则模式，例如 basic、badge_flow、extended_roles。
    """
    config_path = resolve_config_path(
        config,
        participation=participation,
        rules=rules,
    )
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
    """werewolf TUI 命令的入口点。"""
    fire.Fire(main)


if __name__ == "__main__":
    entry()
