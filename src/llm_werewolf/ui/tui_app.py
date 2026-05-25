import uuid
from typing import ClassVar
import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import Input, Label, Button, Footer, Header, Select, Static, Switch
from textual.containers import Vertical, Container, Horizontal

from llm_werewolf.ui.components import ChatPanel, GamePanel, PlayerPanel
from llm_werewolf.game_runtime.types import PlayerProtocol
from llm_werewolf.ui.tui_human_input import TextualHumanInputProvider
from llm_werewolf.game_runtime.engine import GameEngine
from llm_werewolf.game_runtime.events import Event
from llm_werewolf.interface.human_input import is_human_agent
from llm_werewolf.interface.tui_runtime import TUIRuntime, TUIRunSettings, create_tui_runtime


class WerewolfTUI(App):
    """狼人杀游戏的 Textual TUI 应用。"""

    CSS = """
    Screen {
        background: $surface;
    }

    #setup_container {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #setup_panel {
        width: 72;
        max-width: 90%;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $panel;
    }

    #setup_panel Label {
        margin-top: 1;
    }

    #start_game {
        margin-top: 2;
        width: 100%;
    }

    #setup_error {
        margin-top: 1;
        color: $error;
    }

    #game_container {
        height: 100%;
        width: 100%;
        layout: vertical;
    }

    #top_container {
        height: 33%;
        width: 100%;
    }

    #bottom_container {
        height: 1fr;
        width: 100%;
    }

    #human_input_bar {
        height: 9;
        min-height: 9;
        border: solid $accent;
        padding: 0 1;
        background: $panel;
    }

    #human_prompt {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
    }

    #human_input_controls {
        width: 100%;
        height: 3;
    }

    #human_input_box {
        width: 42%;
        margin-top: 0;
    }

    #human_feedback {
        width: 58%;
        height: 100%;
        padding: 0 1;
        color: $warning;
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

    def __init__(
        self,
        game_engine: GameEngine | None = None,
        startup_settings: TUIRunSettings | None = None,
    ) -> None:
        """初始化 TUI 应用。"""
        super().__init__()
        self.game_engine = game_engine
        self.startup_settings = startup_settings or TUIRunSettings()
        self.runtime: TUIRuntime | None = None
        self.viewer_id: str | None = None
        self.session_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now()

        self.player_panel: PlayerPanel | None = None
        self.game_panel: GamePanel | None = None
        self.chat_panel: ChatPanel | None = None
        self.human_prompt: Static | None = None
        self.human_feedback: Static | None = None
        self.human_input: Input | None = None
        self._human_input_future: asyncio.Future[str] | None = None

    def compose(self) -> ComposeResult:
        """组合 TUI 布局。"""
        yield Header(show_clock=True)

        with Container(id="setup_container"), Vertical(id="setup_panel"):
            yield Label("对局模式")
            yield Select(
                [
                    ("纯 LLM 对战", "all_agent"),
                    ("人机对战", "human_mixed"),
                ],
                value=self.startup_settings.participation,
                id="mode_select",
            )
            yield Label("玩家人数")
            yield Input(
                value=str(self.startup_settings.num_players or 12),
                placeholder="6-20",
                id="num_players_input",
            )
            yield Label("警徽流")
            yield Switch(
                value=bool(self.startup_settings.enable_sheriff),
                id="sheriff_switch",
            )
            yield Label("显示 Agent 原始输出")
            yield Switch(
                value=self.startup_settings.show_agent_raw,
                id="raw_output_switch",
            )
            yield Button("开始游戏", id="start_game", variant="primary")
            yield Static("", id="setup_error")

        with Container(id="game_container"):
            with Horizontal(id="top_container"):
                with Vertical(id="player_section"):
                    self.player_panel = PlayerPanel()
                    yield self.player_panel

                with Vertical(id="game_section"):
                    self.game_panel = GamePanel()
                    yield self.game_panel

            with Vertical(id="bottom_container"):
                self.chat_panel = ChatPanel()
                yield self.chat_panel

            with Vertical(id="human_input_bar"):
                self.human_prompt = Static("等待开局。", id="human_prompt")
                yield self.human_prompt
                with Horizontal(id="human_input_controls"):
                    self.human_input = Input(
                        placeholder="等待真人操作...",
                        id="human_input_box",
                        disabled=True,
                    )
                    yield self.human_input
                    self.human_feedback = Static("", id="human_feedback")
                    yield self.human_feedback

        yield Footer()

    def on_mount(self) -> None:
        """应用挂载时调用。"""
        self.title = "Werewolf Game"
        self.sub_title = f"AI-Powered Werewolf | Session: {self.session_id}"

        self.show_setup_view()
        if self.game_engine and self.game_engine.game_state:
            self._show_game_view()
            self.update_game_state()
            self.game_engine.on_event = self.on_game_event
            self.run_worker(self._run_game, exclusive=True)

        self.set_interval(1.0, self.update_footer)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理设置页按钮。"""
        if event.button.id == "start_game":
            await self.start_game_from_settings()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理真人玩家输入提交。"""
        if event.input.id != "human_input_box":
            return
        value = event.value.strip()
        event.input.value = ""
        event.input.disabled = True
        if self.human_prompt:
            self.human_prompt.update("处理中，等待游戏继续...")
        if self._human_input_future is not None and not self._human_input_future.done():
            self._human_input_future.set_result(value)

    async def start_game_from_settings(self) -> None:
        """从设置页读取配置并启动游戏。"""
        settings = self._read_settings_from_widgets()
        if settings is None:
            return

        try:
            runtime = create_tui_runtime(settings)
        except Exception as exc:
            self._show_setup_error(f"启动失败: {exc}")
            return

        self.apply_runtime(runtime)
        if self.chat_panel:
            self.chat_panel.add_system_message(
                f"已创建 {runtime.num_players} 人对局，警徽流: "
                f"{'开启' if runtime.engine.config.enable_sheriff else '关闭'}。"
            )
        self.run_worker(self._run_game, exclusive=True)

    def apply_runtime(self, runtime: TUIRuntime) -> None:
        """把已创建的运行时绑定到 TUI。"""
        self.runtime = runtime
        self.game_engine = runtime.engine
        self.viewer_id = None

        if runtime.participation == "human_mixed":
            human_player = self._find_single_human_player()
            self.viewer_id = human_player.player_id
            runtime.engine.phase_interaction.set_human_input_provider(
                TextualHumanInputProvider(self)
            )
            self._set_input_idle("等待你的回合。")
        else:
            self._set_input_idle("纯 LLM 观战模式。")

        runtime.engine.on_event = self.on_game_event
        self._show_game_view()
        self.update_game_state()

    async def request_human_input(self, prompt: str, *, mode: str) -> str:
        """供 TextualHumanInputProvider 等待输入框提交。"""
        if self.human_input is None or self.human_prompt is None:
            msg = "TUI human input widgets are not mounted."
            raise RuntimeError(msg)
        if self._human_input_future is not None and not self._human_input_future.done():
            msg = "A human input prompt is already active."
            raise RuntimeError(msg)

        loop = asyncio.get_running_loop()
        self._human_input_future = loop.create_future()
        self.human_prompt.update(prompt)
        if self.human_feedback:
            self.human_feedback.update("")
        self.human_input.placeholder = "输入数字并回车" if mode == "number" else "输入文字并回车"
        self.human_input.disabled = False
        self.call_after_refresh(self.human_input.focus)
        return await self._human_input_future

    def show_human_feedback(self, message: str) -> None:
        """展示人类输入校验反馈。"""
        if self.human_feedback:
            self.human_feedback.update(message)
        if self.chat_panel:
            self.chat_panel.add_system_message(message)

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
        """处理游戏事件。"""
        if self.chat_panel:
            self.chat_panel.add_event(event, viewer_id=self.viewer_id)

        self.update_game_state()

    def add_system_message(self, message: str) -> None:
        """向聊天区添加系统消息。"""
        if self.chat_panel:
            self.chat_panel.add_system_message(message)

    def add_error(self, error: str) -> None:
        """向聊天区添加错误消息。"""
        if self.chat_panel:
            self.chat_panel.add_system_message(f"ERROR: {error}")

    def show_setup_view(self) -> None:
        setup = self.query_one("#setup_container")
        game = self.query_one("#game_container")
        setup.display = True
        game.display = False

    def _show_game_view(self) -> None:
        if not getattr(self, "_screen_stack", None):
            return
        setup = self.query_one("#setup_container")
        game = self.query_one("#game_container")
        setup.display = False
        game.display = True

    def _read_settings_from_widgets(self) -> TUIRunSettings | None:
        mode = str(self.query_one("#mode_select", Select).value)
        num_players_text = self.query_one("#num_players_input", Input).value.strip()
        if not num_players_text.isdigit():
            self._show_setup_error("玩家人数必须是 6-20 的数字。")
            return None
        num_players = int(num_players_text)
        if not 6 <= num_players <= 20:
            self._show_setup_error("玩家人数必须在 6-20 之间。")
            return None

        return TUIRunSettings(
            config=self.startup_settings.config,
            participation=mode,
            rules=self.startup_settings.rules,
            num_players=num_players,
            enable_sheriff=self.query_one("#sheriff_switch", Switch).value,
            show_agent_raw=self.query_one("#raw_output_switch", Switch).value,
        )

    def _show_setup_error(self, message: str) -> None:
        self.query_one("#setup_error", Static).update(message)

    def _set_input_idle(self, message: str) -> None:
        if self.human_prompt:
            self.human_prompt.update(message)
        if self.human_feedback:
            self.human_feedback.update("")
        if self.human_input:
            self.human_input.disabled = True
            self.human_input.placeholder = "等待真人操作..."

    def _find_single_human_player(self) -> PlayerProtocol:
        if not self.game_engine or not self.game_engine.game_state:
            msg = "human_mixed TUI mode requires an initialized game state"
            raise ValueError(msg)

        human_players = [
            player
            for player in self.game_engine.game_state.players
            if player.agent is not None and is_human_agent(player.agent)
        ]
        if len(human_players) != 1:
            msg = "human_mixed TUI mode requires exactly one human player"
            raise ValueError(msg)
        return human_players[0]


def run_tui(
    game_engine: GameEngine | None = None,
    *,
    startup_settings: TUIRunSettings | None = None,
) -> None:
    """运行 TUI 应用。"""
    app = WerewolfTUI(game_engine=game_engine, startup_settings=startup_settings)
    app.run()
