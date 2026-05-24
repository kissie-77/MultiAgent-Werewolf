from typing import Any

from rich.table import Table
from textual.widgets import RichLog

from llm_werewolf.game_runtime.game_state import GameState


class PlayerPanel(RichLog):
    """展示玩家列表及其状态的组件。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """初始化玩家面板。"""
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
            return

        # 清除先前内容
        self.clear()

        # 检查游戏中是否存在人类玩家
        has_human_player = any(p.ai_model == "human" for p in self.game_state.players)

        # 创建无标题表格
        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 1),
            collapse_padding=True,
        )
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Model", style="blue", no_wrap=True)
        table.add_column("Status", style="green", no_wrap=True)
        table.add_column("Role", style="yellow", no_wrap=True)

        for player in self.game_state.players:
            # 确定状态图标
            if player.is_alive():
                status_icon = "✓"
                status_style = "green"
            else:
                status_icon = "✗"
                status_style = "red"

            # 角色展示逻辑：
            # - 若存在人类玩家：隐藏角色（显示 "?"），除非已死亡
            # - 若无人类玩家：展示所有角色（观战/测试模式）
            if has_human_player:
                role_display = player.get_role_name() if not player.is_alive() else "?"
            else:
                role_display = player.get_role_name()

            # 添加特殊状态指示
            status_text = status_icon
            if player.has_status("protected"):
                status_text += " 🛡️"
            if player.has_status("poisoned"):
                status_text += " ☠️"
            if player.has_status("marked"):
                status_text += " 🔴"
            if player.has_status("lover"):
                status_text += " ❤️"

            table.add_row(
                player.name,
                player.ai_model,
                f"[{status_style}]{status_text}[/{status_style}]",
                role_display,
            )

        # 将表格写入 RichLog
        self.write(table)

    def on_mount(self) -> None:
        """组件挂载时调用。"""
        self.refresh_display()
