import asyncio
import sys

import fire
import logfire
from rich.console import Console

from llm_werewolf.game_runtime.env import load_project_dotenv

load_project_dotenv()

# Windows: keep Rich emoji / zh output UTF-8 when piping or logging.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from llm_werewolf.paths import RUNS_DIR
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.interface.cli.runtime.modes import resolve_config_path
from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.interface.cli.runtime.bootstrap import (
    prepare_game_roster,
    create_information_hub,
    wire_agentscope_after_setup,
)
from llm_werewolf.interface.cli.runtime.startup_menu import prompt_startup_selection
from llm_werewolf.ui.console_presenter import ConsolePresenter

console = Console()


def _human_viewer_ids(engine: GameEngine) -> list[str]:
    if engine.game_state is None:
        return []
    viewer_ids: list[str] = []
    for player in engine.game_state.players:
        agent = getattr(player, "agent", None)
        if getattr(agent, "model", "") == "human":
            viewer_ids.append(player.player_id)
    return viewer_ids


def _announce_human_identity(engine: GameEngine, locale: Locale) -> None:
    if engine.game_state is None:
        return
    human_players = [
        player
        for player in engine.game_state.players
        if getattr(getattr(player, "agent", None), "model", "") == "human"
    ]
    if not human_players:
        return

    console.print()
    console.print("─" * 70, style="cyan")
    for player in human_players:
        console.print(f"[bold cyan]你的座位：{player.name}（{player.player_id}）[/bold cyan]")
        console.print(f"[bold cyan]你的身份：{player.get_role_name()}[/bold cyan]")
    console.print("─" * 70, style="cyan")
    console.print()


async def main(
    config: str | None = None,
    participation: str = "all_agent",
    rules: str = "badge_flow",
    players: int | None = None,
    human_seat: str | None = None,
    plan_assignment: str | None = None,
    plan_assignment_seed: int | None = None,
    badge_flow: bool = False,
) -> None:
    """在控制台模式下运行狼人杀游戏（自动进行）。

    Args:
        config: YAML 配置文件路径；提供后优先于模式选择。
        participation: 参与方式，例如 all_agent。
        rules: 规则模式，例如 basic、badge_flow、extended_roles。
        players: 覆盖总座位数（含人类座位），范围 6-20；缺省沿用 YAML 名单。
        human_seat: 人类玩家的 1-based 座位号，可用逗号分隔多个（如 "1,3"）；缺省为纯 Agent 局。
        plan_assignment: 覆盖开局 plan 分流：off、role_cycle 或 role_random。
        plan_assignment_seed: role_random 的复现种子；也可覆盖 YAML 中的 seed。
        badge_flow: 是否开启警长 / 警徽流（首夜后的警长选举）；缺省关闭，行为与现状一致。
    """
    config_path = resolve_config_path(config, participation=participation, rules=rules)
    players_config = load_config(config_path=config_path)

    try:
        if players is not None:
            from llm_werewolf.interface.cli.runtime.player_count import resize_players_config

            players_config = resize_players_config(players_config, int(players))
        if human_seat is not None:
            from llm_werewolf.interface.cli.runtime.overrides import parse_seat_list, apply_human_seats

            players_config = apply_human_seats(players_config, parse_seat_list(human_seat))
        if plan_assignment is not None or plan_assignment_seed is not None:
            from llm_werewolf.interface.cli.runtime.overrides import apply_plan_assignment_override

            players_config = apply_plan_assignment_override(
                players_config,
                plan_assignment,
                seed=plan_assignment_seed,
            )
    except (ValueError, TypeError) as exc:
        console.print(f"[red]参数错误: {exc}[/red]")
        return

    num_players = len(players_config.players)
    agents, roles, game_config = prepare_game_roster(players_config)
    if badge_flow or rules == "badge_flow":
        game_config = game_config.model_copy(update={"enable_sheriff": True})

    locale = Locale(players_config.language)
    engine = GameEngine(
        game_config, language=players_config.language, information_hub=create_information_hub()
    )
    presenter = ConsolePresenter(locale)
    engine.on_event = presenter.present_event

    engine.setup_game(players=agents, roles=roles)
    human_viewers = _human_viewer_ids(engine)

    if len(human_viewers) == 1:
        viewer_id = human_viewers[0]
        engine.on_event = lambda event: presenter.present_event(event, viewer_id=viewer_id)
    else:
        engine.on_event = presenter.present_event

    wire_agentscope_after_setup(engine, players_config)

    logfire.info("game_created", config_path=str(config_path), num_players=num_players)

    console.print(
        f"[green]{locale.get('config_loaded', config_path=config_path.resolve())}[/green]"
    )
    console.print(f"[cyan]{locale.get('player_count_info', num_players=num_players)}[/cyan]")
    console.print(f"[cyan]{locale.get('interface_mode')}[/cyan]")
    _announce_human_identity(engine, locale)

    try:
        result = await engine.play_game()
        console.print(f"\n{result}")

        from datetime import datetime

        from llm_werewolf.interface.cli.runtime.finalize_run import finalize_run

        run_dir = RUNS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
        post = await finalize_run(
            engine,
            run_dir,
            game_result_text=result,
            config_path=config_path,
            prompt_version=players_config.prompt_version,
        )
        if post.error:
            console.print(f"[yellow]赛后分析部分失败: {post.error}[/yellow]")
        console.print(
            f"[dim]赛后产物已写入 {run_dir.resolve()} ({', '.join(post.artifacts[:4])}…)[/dim]"
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
    players: int | None = None,
    human_seat: str | None = None,
    plan_assignment: str | None = None,
    plan_assignment_seed: int | None = None,
    badge_flow: bool = False,
) -> None:
    """同步包装器，用于运行异步 main 函数。"""
    asyncio.run(
        main(
            config,
            participation=participation,
            rules=rules,
            players=players,
            human_seat=human_seat,
            plan_assignment=plan_assignment,
            plan_assignment_seed=plan_assignment_seed,
            badge_flow=badge_flow,
        )
    )


def entry() -> None:
    """Werewolf 控制台命令的入口点。"""
    if len(sys.argv) == 1:
        selection = prompt_startup_selection()
        asyncio.run(
            main(
                participation=selection.participation,
                rules=selection.rules,
                human_seat=selection.human_seat,
                players=selection.players,
            )
        )
        return
    fire.Fire(_run_main)


if __name__ == "__main__":
    entry()
