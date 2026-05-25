import fire

from llm_werewolf.game_runtime.env import load_project_dotenv

load_project_dotenv()

from llm_werewolf.interface.tui_runtime import TUIRunSettings
from llm_werewolf.ui import run_tui


def main(
    config: str | None = None,
    participation: str = "all_agent",
    rules: str = "badge_flow",
    num_players: int | None = None,
    enable_sheriff: bool | None = None,
    show_agent_raw: bool = False,
) -> None:
    """使用 TUI 界面运行狼人杀游戏。"""
    startup_settings = TUIRunSettings(
        config=config,
        participation=participation,
        rules=rules,
        num_players=num_players,
        enable_sheriff=enable_sheriff,
        show_agent_raw=show_agent_raw,
    )
    run_tui(startup_settings=startup_settings)


def entry() -> None:
    """Werewolf TUI 命令的入口点。"""
    fire.Fire(main)


if __name__ == "__main__":
    entry()
