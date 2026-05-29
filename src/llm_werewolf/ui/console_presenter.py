"""控制台展示器，用于美化游戏输出。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.console import Console

from llm_werewolf.game_runtime.types import Event, EventType

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.locale import Locale

console = Console()


class ConsolePresenter:
    """以美化格式展示游戏事件，并控制合适的输出节奏。"""

    def __init__(self, locale: Locale) -> None:
        """初始化控制台展示器。

        Args:
            locale: 用于本地化字符串的 Locale 实例。
        """
        self.locale = locale
        self._last_phase = ""
        self._last_round = -1
        self._night_actions: list[str] = []
        self._vote_buffer: dict[str, list[str]] = {}  # 目标名 -> [投票者]
        self._in_voting_phase = False
        self._discussion_messages: list[str] = []
        self._werewolf_discussion: list[str] = []

    def _is_night_action_event(self, event_type: EventType) -> bool:
        """判断事件类型是否为应缓冲的夜间行动。

        Args:
            event_type: 待检查的事件类型。

        Returns:
            bool: 若应缓冲则返回 True。
        """
        return event_type in {
            EventType.GUARD_PROTECTED,
            EventType.WITCH_SAVED,
            EventType.WITCH_POISONED,
            EventType.SEER_CHECKED,
            EventType.WEREWOLF_KILLED,
            EventType.LOVERS_LINKED,
        }

    def _is_sheriff_event(self, event_type: EventType) -> bool:
        """判断事件类型是否与警长相关。

        Args:
            event_type: 待检查的事件类型。

        Returns:
            bool: 若为警长相关事件则返回 True。
        """
        return event_type in {
            EventType.SHERIFF_CAMPAIGN_STARTED,
            EventType.SHERIFF_CANDIDATE_SPEECH,
            EventType.SHERIFF_VOTE_CAST,
            EventType.SHERIFF_ELECTED,
            EventType.SHERIFF_BADGE_TRANSFERRED,
        }

    def _handle_special_events(self, event: Event) -> bool:
        """处理特殊事件类型，并返回是否已处理。

        Args:
            event: 待处理的事件。

        Returns:
            bool: 若已处理则返回 True，否则返回 False。
        """
        if event.event_type == EventType.HUNTER_REVENGE:
            self._present_hunter_revenge(event)
            return True

        if self._is_sheriff_event(event.event_type):
            self._present_sheriff_event(event)
            return True

        if event.event_type == EventType.ROLE_REVEALED:
            self._present_role_reveal(event)
            return True

        return False

    def _handle_game_lifecycle_events(self, event: Event) -> bool:
        """处理游戏生命周期事件（开始、结束）。

        Args:
            event: 待处理的事件。

        Returns:
            bool: 若已处理则返回 True，否则返回 False。
        """
        if event.event_type == EventType.GAME_STARTED:
            self._present_game_start(event)
            return True
        if event.event_type == EventType.GAME_ENDED:
            self._present_game_end(event)
            return True
        return False

    def _handle_player_events(self, event: Event) -> bool:
        """处理玩家相关事件（发言、死亡、出局）。

        Args:
            event: 待处理的事件。

        Returns:
            bool: 若已处理则返回 True，否则返回 False。
        """
        if event.event_type == EventType.PLAYER_DIED:
            self._present_death(event)
            return True
        if event.event_type == EventType.PLAYER_SPEECH:
            self._buffer_discussion(event)
            return True
        if event.event_type == EventType.PLAYER_DISCUSSION:
            self._buffer_werewolf_discussion(event)
            return True
        if event.event_type == EventType.PLAYER_ELIMINATED:
            self._present_elimination(event)
            return True
        return False

    def _handle_voting_events(self, event: Event) -> bool:
        """处理投票相关事件。

        Args:
            event: 待处理的事件。

        Returns:
            bool: 若已处理则返回 True，否则返回 False。
        """
        if event.event_type == EventType.VOTE_CAST:
            self._buffer_vote(event)
            return True
        if event.event_type == EventType.VOTE_RESULT:
            if "📊" in event.message or "統計" in event.message:
                self._flush_votes()
            return True
        return False

    def present_event(self, event: Event, viewer_id: str | None = None) -> None:
        """以合适格式展示事件。

        Args:
            event: 待展示的事件。
            viewer_id: 若指定，则仅展示该玩家可见的事件（为 None 时为上帝视角）。
        """
        if viewer_id is not None and not event.is_visible_to(viewer_id):
            return
        if viewer_id is not None and self._is_night_action_event(event.event_type):
            return

        # 处理阶段切换
        if event.event_type == EventType.PHASE_CHANGED:
            self._handle_phase_change(event)
        # 处理不同类别的事件
        elif self._handle_game_lifecycle_events(event):
            pass  # 已处理
        elif event.event_type == EventType.MESSAGE:
            self._handle_narrator_message(event)
        elif event.event_type == EventType.ROLE_ACTING:
            pass  # 缓冲夜间行动
        elif self._is_night_action_event(event.event_type):
            self._buffer_night_action(event)
        elif (
            self._handle_player_events(event)
            or self._handle_voting_events(event)
            or self._handle_special_events(event)
        ):
            pass  # 已处理
        else:
            # 默认：以合适样式打印
            style = self._get_event_style(event.event_type)
            console.print(event.message, style=style)

    def _handle_phase_change(self, event: Event) -> None:
        """处理阶段切换并输出视觉分隔符。"""
        if event.data and event.data.get("phase") == "night":
            # 入夜前刷新已缓冲内容（但不刷新狼人讨论）
            self._flush_discussion()
            self._flush_votes()

            round_num = event.data.get("round", 0)
            console.print()
            console.print("═" * 70, style="blue")
            console.print(f"                    🌙 第 {round_num} 輪 - 黑夜 🌙", style="bold blue")
            console.print("═" * 70, style="blue")
            console.print()
        elif event.data and event.data.get("phase") == "day":
            # 入昼前刷新夜间行动和狼人讨论
            self._flush_night_actions()

            round_num = event.data.get("round", 0)
            console.print()
            console.print("═" * 70, style="yellow")
            console.print(
                f"                    ☀️  第 {round_num} 輪 - 白天 ☀️", style="bold yellow"
            )
            console.print("═" * 70, style="yellow")
            console.print()

    def _handle_narrator_message(self, event: Event) -> None:
        """处理旁白类事件。"""
        if not event.data:
            console.print(event.message, style="dim italic")
            return

        action = event.data.get("action", "")

        if action == "night_falls":
            console.print("🌙 天黑請閉眼...", style="bold blue")
        elif action == "werewolves_wake":
            console.print()
            console.print("🐺 狼人，請睜眼...", style="bold red")
            console.print()
        elif action == "werewolves_vote":
            # 投票前先刷新狼人讨论
            self._flush_werewolf_discussion()
            console.print()
            console.print("🐺 狼人正在选择目标...", style="dim red")
        elif action == "werewolves_sleep":
            # 狼人闭眼时刷新夜间行动
            self._flush_night_actions()
            console.print()
            console.print("🐺 狼人，請閉眼...", style="bold blue")
        elif action == "daybreak":
            console.print("☀️  天亮了，所有人請睜眼...", style="bold yellow")
        else:
            console.print(event.message, style="dim italic")

    def _buffer_night_action(self, event: Event) -> None:
        """缓冲夜间行动以便分组展示。"""
        # 提取干净文案（若已有 emoji 则去掉）
        message = event.message
        for emoji in ["🛡️", "💊", "☠️", "🔮", "🐺", "💕", "🐺💋"]:
            message = message.replace(emoji, "").strip()

        # 为行动配上 emoji
        if event.event_type == EventType.GUARD_PROTECTED:
            icon = "🛡️"
        elif event.event_type == EventType.WITCH_SAVED:
            icon = "💊"
        elif event.event_type == EventType.WITCH_POISONED:
            icon = "☠️"
        elif event.event_type == EventType.SEER_CHECKED:
            icon = "🔮"
        elif event.event_type == EventType.WEREWOLF_KILLED:
            icon = "🐺"
        elif event.event_type == EventType.LOVERS_LINKED:
            icon = "💕"
        else:
            icon = "  "

        self._night_actions.append(f"{icon} {message}")

    def _flush_night_actions(self) -> None:
        """展示所有已缓冲的夜间行动。"""
        if not self._night_actions:
            return

        console.print()
        console.print("─── 夜晚行動結果 ───", style="dim cyan")
        for action in self._night_actions:
            console.print(f"   {action}", style="cyan")
        console.print()

        self._night_actions = []

    def _buffer_discussion(self, event: Event) -> None:
        """缓冲讨论消息以便分组展示。"""
        if event.data:
            player_name = event.data.get("player_name", "Unknown")
            speech = event.data.get("speech", "")
            self._discussion_messages.append(f"{player_name}: {speech}")

    def _buffer_werewolf_discussion(self, event: Event) -> None:
        """缓冲狼人讨论以便分组展示。"""
        if event.data:
            player_name = event.data.get("player_name", "Unknown")
            speech = event.data.get("speech", "")
            self._werewolf_discussion.append(f"🐺 {player_name}: {speech}")

    def _flush_werewolf_discussion(self) -> None:
        """展示狼人讨论（仅在夜晚阶段调用）。"""
        if self._werewolf_discussion:
            console.print()
            panel = Panel(
                "\n".join(self._werewolf_discussion),
                title="狼人討論",
                border_style="red",
                padding=(1, 2),
            )
            console.print(panel)
            self._werewolf_discussion = []

    def _flush_discussion(self) -> None:
        """展示所有已缓冲的玩家发言。"""
        if self._discussion_messages:
            console.print()
            console.print("💬 玩家發言", style="bold cyan")
            console.print("─" * 70, style="dim")
            for msg in self._discussion_messages:
                console.print(f"   {msg}", style="cyan")
            console.print()
            self._discussion_messages = []

    def _buffer_vote(self, event: Event) -> None:
        """缓冲投票以便分组展示。"""
        if event.data:
            target_name = event.data.get("target_name", "Unknown")
            voter_name = event.data.get("voter_name", "Unknown")
            if target_name not in self._vote_buffer:
                self._vote_buffer[target_name] = []
            self._vote_buffer[target_name].append(voter_name)

    def _flush_votes(self) -> None:
        """以表格形式展示所有已缓冲的投票。"""
        if not self._vote_buffer:
            return

        # 先刷新讨论区
        self._flush_discussion()

        console.print()
        console.print("🗳️  投票階段", style="bold yellow")
        console.print()

        # 构建投票汇总表
        table = Table(show_header=True, header_style="bold yellow", box=None)
        table.add_column("排名", justify="center", width=6)
        table.add_column("候選人", style="cyan", width=20)
        table.add_column("票數", justify="center", style="yellow", width=8)
        table.add_column("投票者", style="dim")

        # 按得票数排序
        sorted_votes = sorted(self._vote_buffer.items(), key=lambda x: len(x[1]), reverse=True)

        # 添加名次 emoji
        rank_emoji = {0: "🥇", 1: "🥈", 2: "🥉"}

        for idx, (target, voters) in enumerate(sorted_votes):
            vote_count = len(voters)
            voters_str = ", ".join(voters)
            rank = rank_emoji.get(idx, "  ")
            table.add_row(rank, target, str(vote_count), voters_str)

        console.print(table)
        console.print()

        self._vote_buffer = {}

    def _present_game_start(self, event: Event) -> None:
        """展示游戏开始。"""
        console.print()
        console.print("═" * 70, style="bold green")
        console.print("                      🎮 遊戲開始 🎮", style="bold green")
        console.print("═" * 70, style="bold green")
        if event.data:
            player_count = event.data.get("player_count", 0)
            console.print(f"\n📋 玩家人數：{player_count} 人\n", style="green")

    def _present_game_end(self, event: Event) -> None:
        """展示游戏结束。"""
        console.print()
        console.print("═" * 70, style="bold magenta")
        console.print("                      🏆 遊戲結束 🏆", style="bold magenta")
        console.print("═" * 70, style="bold magenta")
        console.print()
        console.print(event.message, style="bold magenta")
        console.print()

    def _present_death(self, event: Event) -> None:
        """展示玩家死亡。"""
        console.print(f"💀 {event.message}", style="bold red")

    def _present_elimination(self, event: Event) -> None:
        """展示玩家出局。"""
        console.print()
        console.print(f"⚰️  {event.message}", style="bold red")
        console.print()

    def _present_hunter_revenge(self, event: Event) -> None:
        """展示猎人开枪。"""
        console.print(f"🏹 {event.message}", style="bold yellow")

    def _present_sheriff_event(self, event: Event) -> None:
        """展示警长相关事件。"""
        console.print(f"🎖️  {event.message}", style="gold1")

    def _present_role_reveal(self, event: Event) -> None:
        """展示身份揭示。"""
        console.print(f"🎭 {event.message}", style="bold magenta")

    def _get_event_style(self, event_type: EventType) -> str:
        """按事件类型返回展示样式。"""
        styles = {
            EventType.ERROR: "bold red",
            EventType.PLAYER_DIED: "red",
            EventType.PLAYER_ELIMINATED: "bold red",
            EventType.HUNTER_REVENGE: "yellow",
            EventType.VOTE_RESULT: "yellow",
        }
        return styles.get(event_type, "white")
