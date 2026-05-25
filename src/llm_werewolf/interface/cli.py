import asyncio
from pathlib import Path

import fire
import logfire
from rich.console import Console

from llm_werewolf.game_runtime.env import load_project_dotenv

load_project_dotenv()

from llm_werewolf.interface.bootstrap import (
    prepare_game_roster,
    wire_agentscope_after_setup,
)
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.interface.human_input import ShellHumanInputProvider, is_human_agent
from llm_werewolf.interface.modes import resolve_config_path
from llm_werewolf.ui.console_presenter import ConsolePresenter

console = Console()


def _find_single_human_player(game_state):
    human_players = [
        player
        for player in game_state.players
        if player.agent is not None and is_human_agent(player.agent)
    ]
    if len(human_players) != 1:
        msg = "human_mixed CLI mode requires exactly one human player"
        raise ValueError(msg)
    return human_players[0]


async def main(
    config: str | None = None,
    participation: str = "all_agent",
    rules: str = "badge_flow",
) -> None:
    """在控制台模式下运行狼人杀游戏（自动进行）。

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

    locale = Locale(players_config.language)
    engine = GameEngine(game_config, language=players_config.language)

    presenter = ConsolePresenter(locale)
    engine.on_event = presenter.present_event

    engine.setup_game(players=players, roles=roles)
    wire_agentscope_after_setup(engine, players_config)

    if participation == "human_mixed":
        human_player = _find_single_human_player(engine.game_state)
        engine.phase_interaction.set_human_input_provider(ShellHumanInputProvider())
        engine.on_event = lambda event: presenter.present_event(
            event,
            viewer_id=human_player.player_id,
        )

    logfire.info("game_created", config_path=str(config_path), num_players=num_players)

    console.print(
        f"[green]{locale.get('config_loaded', config_path=config_path.resolve())}[/green]"
    )
    console.print(f"[cyan]{locale.get('player_count_info', num_players=num_players)}[/cyan]")
    console.print(f"[cyan]{locale.get('interface_mode')}[/cyan]")

    try:
        result = await engine.play_game()
        console.print(f"\n{result}")

        if engine.game_state and engine.game_state.vote_intention_tracker is not None:
            from datetime import datetime

            from llm_werewolf.evaluation.vote_swing_analysis import write_persuasion_artifacts

            run_dir = Path("runs") / datetime.now().strftime("%Y%m%d-%H%M%S")
            run_dir.mkdir(parents=True, exist_ok=True)
            engine.game_state.vote_intention_tracker.save_jsonl(
                run_dir / "vote_intentions.jsonl"
            )
            write_persuasion_artifacts(run_dir)
            console.print(
                f"[dim]投票意向复盘已写入 {run_dir.resolve()} "
                "(vote_intentions.jsonl / vote_swing_report.md)[/dim]"
            )

        if engine.game_state:
            alive = engine.game_state.get_alive_players()
            dead = engine.game_state.get_dead_players()

            console.print(locale.get("alive_players"))
            for player in alive:
                console.print(
                    locale.get("player_role_info", name=player.name, role=player.get_role_name())
                )

            console.print(locale.get("dead_players"))
            for player in dead:
                console.print(
                    locale.get("player_role_info", name=player.name, role=player.get_role_name())
                )

    except KeyboardInterrupt:
        if players_config.language == "zh-TW":
            console.print("\n遊戲已由使用者中止。")
        elif players_config.language == "zh-CN":
            console.print("\n游戏已由用户中止。")
        else:
            console.print("\nGame interrupted by user.")
    except Exception as exc:
        logfire.error(
            "game_execution_error",
            error=str(exc),
            config_path=str(config_path),
            num_players=num_players,
        )
        if players_config.language == "zh-TW":
            console.print(f"[red]執行遊戲時發生錯誤: {exc}[/red]")
        elif players_config.language == "zh-CN":
            console.print(f"[red]执行游戏时发生错误: {exc}[/red]")
        else:
            console.print(f"[red]Error executing game: {exc}[/red]")
        raise


def _run_main(
    config: str | None = None,
    participation: str = "all_agent",
    rules: str = "badge_flow",
) -> None:
    """同步包装器，用于运行异步 main 函数。"""
    asyncio.run(main(config, participation=participation, rules=rules))


def entry() -> None:
    """werewolf 控制台命令的入口点。"""
    fire.Fire(_run_main)


if __name__ == "__main__":
    entry()
