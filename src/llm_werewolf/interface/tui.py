import fire
import logfire

from llm_werewolf.game_runtime.env import load_project_dotenv

load_project_dotenv()

from llm_werewolf.interface.bootstrap import (
    create_information_hub,
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
    players: int | None = None,
    human_seat: str | None = None,
    badge_flow: bool = False,
) -> None:
    """使用 TUI 界面运行狼人杀游戏。

    Args:
        config: YAML 配置文件路径；提供后优先于模式选择。
        participation: 参与方式，例如 all_agent。
        rules: 规则模式，例如 basic、badge_flow、extended_roles。
        players: 覆盖总座位数（含人类座位），范围 6-20；缺省沿用 YAML 名单。
        human_seat: 人类玩家的 1-based 座位号，可用逗号分隔多个；缺省为纯 Agent 局。
        badge_flow: 是否开启警长 / 警徽流；缺省关闭，行为与现状一致。
    """
    config_path = resolve_config_path(
        config,
        participation=participation,
        rules=rules,
    )
    players_config = load_config(config_path=config_path)

    try:
        if players is not None:
            from llm_werewolf.interface.player_count import resize_players_config

            players_config = resize_players_config(players_config, int(players))
        if human_seat is not None:
            from llm_werewolf.interface.cli_overrides import apply_human_seats, parse_seat_list

            players_config = apply_human_seats(players_config, parse_seat_list(human_seat))
    except (ValueError, TypeError) as exc:
        print(f"参数错误: {exc}")
        return

    num_players = len(players_config.players)
    agents, roles, game_config = prepare_game_roster(players_config)
    if badge_flow:
        game_config = game_config.model_copy(update={"enable_sheriff": True})

    engine = GameEngine(
        game_config,
        language=players_config.language,
        information_hub=create_information_hub(),
    )
    engine.setup_game(players=agents, roles=roles)
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
