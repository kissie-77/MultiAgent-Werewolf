from io import StringIO
from typing import Any

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from textual.widgets import Static

from llm_werewolf.game_runtime.game_state import GameState
from llm_werewolf.game_runtime.types import Camp


class GamePanel(Static):
    """展示当前游戏状态的组件。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """初始化游戏面板。"""
        super().__init__(*args, **kwargs)
        self.game_state: GameState | None = None

    def set_game_state(self, game_state: GameState) -> None:
        """设置要展示的游戏状态。

        Args:
            game_state: 当前游戏状态。
        """
        self.game_state = game_state
        self.refresh_display()

    def refresh_display(self) -> None:
        """用当前游戏状态刷新展示。"""
        if not self.game_state:
            self.update("No game in progress")
            return

        # 阶段图标
        phase_icons = {
            "setup": "⚙️",
            "night": "🌙",
            "day_discussion": "☀️",
            "day_voting": "🗳️",
            "ended": "🏁",
        }
        phase_icon = phase_icons.get(self.game_state.phase.value, "❓")

        # 创建主信息文本
        title = Text()
        title.append(f"{phase_icon} ", style="bold")
        title.append(f"Round {self.game_state.round_number}", style="bold yellow")
        title.append(" - ")
        title.append(self.game_state.phase.value.replace("_", " ").title(), style="bold cyan")

        # 创建统计表格
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Label", style="dim")
        stats_table.add_column("Value", style="bold")

        alive_players = len(self.game_state.get_alive_players())
        total_players = len(self.game_state.players)
        werewolves = self.game_state.count_alive_by_camp(Camp.WEREWOLF)
        villagers = self.game_state.count_alive_by_camp(Camp.VILLAGER)

        stats_table.add_row("Total Players:", f"{alive_players}/{total_players}")
        stats_table.add_row(
            "Werewolves:", f"[red]{werewolves}[/red]" if werewolves > 0 else "[dim]0[/dim]"
        )
        stats_table.add_row(
            "Villagers:", f"[green]{villagers}[/green]" if villagers > 0 else "[dim]0[/dim]"
        )

        # 将统计表格渲染为字符串
        console = Console(file=StringIO(), width=40)
        console.print(stats_table)
        stats_content = console.file.getvalue()

        # 投票统计（若在投票阶段）
        vote_content = ""
        if self.game_state.phase.value == "day_voting":
            vote_counts = self.game_state.get_vote_counts()
            if vote_counts:
                vote_table = Table(
                    title="Vote Counts", show_header=True, header_style="bold magenta"
                )
                vote_table.add_column("Player", style="cyan")
                vote_table.add_column("Votes", style="yellow", justify="right")

                for player_id, count in sorted(
                    vote_counts.items(), key=lambda x: x[1], reverse=True
                ):
                    player = self.game_state.get_player(player_id)
                    if player:
                        vote_table.add_row(player.name, str(count))

                console = Console(file=StringIO(), width=40)
                console.print(vote_table)
                vote_content = console.file.getvalue()

        # 合并所有内容
        content = Text.assemble(title, "\n\n")
        content.append(stats_content)

        if vote_content:
            content.append("\n")
            content.append(vote_content)

        panel = Panel(content, title="Game Status", border_style="cyan")
        self.update(panel)

    def on_mount(self) -> None:
        """组件挂载时调用。"""
        self.refresh_display()
