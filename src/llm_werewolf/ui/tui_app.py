import uuid
from typing import ClassVar
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header
from textual.containers import Vertical, Horizontal

from llm_werewolf.ui.components import ChatPanel, GamePanel, PlayerPanel
from llm_werewolf.game_runtime.engine import GameEngine
from llm_werewolf.game_runtime.events.events import Event


class WerewolfTUI(App):
    """狼人杀游戏的 Textual TUI 应用。"""

    CSS = """
    Screen {
        background: $surface;
    }

    #top_container {
        height: 35%;
        width: 100%;
    }

    #bottom_container {
        height: 65%;
        width: 100%;
    }

    #player_section {
        width: 66%;
        height: 100%;
    }

    #game_section {
        width: 34%;
        height: 100%;
    }

    PlayerPanel {
        height: 100%;
        border: solid $primary;
        background: $panel;
    }

    GamePanel {
        height: 100%;
        border: solid $secondary;
        background: $panel;
    }

    ChatPanel {
        height: 100%;
        border: solid $success;
        background: $panel;
    }
    """

    BINDINGS: ClassVar = [("q", "quit", "Quit"), ("ctrl+c", "quit", "Quit")]

    def __init__(self, game_engine: GameEngine | None = None) -> None:
        """初始化 TUI 应用。

        Args:
            game_engine: 要展示的游戏引擎。
        """
        super().__init__()
        self.game_engine = game_engine
        self.session_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now()

        self.player_panel: PlayerPanel | None = None
        self.game_panel: GamePanel | None = None
        self.chat_panel: ChatPanel | None = None

    def compose(self) -> ComposeResult:
        """组合 TUI 布局。

        布局：
        - 上方（35%）：玩家（左 2/3）| 游戏状态（右 1/3）
        - 下方（65%）：聊天/终端输出（全宽）

        Yields:
            Textual UI 组件。
        """
        yield Header(show_clock=True)

        # 顶部容器：玩家与游戏状态并排
        with Horizontal(id="top_container"):
            with Vertical(id="player_section"):
                self.player_panel = PlayerPanel()
                yield self.player_panel

            with Vertical(id="game_section"):
                self.game_panel = GamePanel()
                yield self.game_panel

        # 底部容器：聊天/终端输出
        with Vertical(id="bottom_container"):
            self.chat_panel = ChatPanel()
            yield self.chat_panel

        yield Footer()

    def on_mount(self) -> None:
        """应用挂载时调用。"""
        self.title = "🐺 Werewolf Game"
        self.sub_title = f"AI-Powered Werewolf | Session: {self.session_id}"

        if self.game_engine and self.game_engine.game_state:
            self.update_game_state()

            self.game_engine.on_event = self.on_game_event

            # 在后台自动启动游戏
            self.run_worker(self._run_game, exclusive=True)

        # 每秒更新页脚运行时长
        self.set_interval(1.0, self.update_footer)

    async def _run_game(self) -> None:
        """在后台 worker 中运行游戏。"""
        if self.game_engine:
            await self.game_engine.play_game()

    def update_footer(self) -> None:
        """更新页脚中的当前运行时长。"""
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.sub_title = f"AI-Powered Werewolf | Session: {self.session_id} | Uptime: {uptime_str}"

    def update_game_state(self) -> None:
        """用当前游戏状态更新所有面板。"""
        if not self.game_engine or not self.game_engine.game_state:
            return

        if self.player_panel:
            self.player_panel.set_game_state(self.game_engine.game_state)

        if self.game_panel:
            self.game_panel.set_game_state(self.game_engine.game_state)

    def on_game_event(self, event: Event) -> None:
        """处理游戏事件。

        Args:
            event: 游戏事件。
        """
        if self.chat_panel:
            self.chat_panel.add_event(event)

        self.update_game_state()

    def add_system_message(self, message: str) -> None:
        """向聊天区添加系统消息。

        Args:
            message: 要添加的消息。
        """
        if self.chat_panel:
            self.chat_panel.add_system_message(message)

    def add_error(self, error: str) -> None:
        """向聊天区添加错误消息。

        Args:
            error: 错误消息。
        """
        if self.chat_panel:
            self.chat_panel.add_system_message(f"ERROR: {error}")


def run_tui(game_engine: GameEngine) -> None:
    """运行 TUI 应用。

    Args:
        game_engine: 要展示的游戏引擎。
    """
    app = WerewolfTUI(game_engine=game_engine)
    app.run()
