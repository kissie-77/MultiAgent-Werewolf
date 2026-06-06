"""控制台展示器，用于美化游戏输出。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.console import Console

from llm_werewolf.game_runtime.types import Event, EventType

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.i18n.locale import Locale

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
        self._delayed_night_public_events: list[Event] = []

    def _is_traditional_chinese(self) -> bool:
        return getattr(self.locale, "language", "") == "zh-TW"

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
            EventType.WITCH_POISON_USED,
            EventType.WITCH_POISONED,
            EventType.SEER_CHECKED,
            EventType.WEREWOLF_KILLED,
            EventType.LOVERS_LINKED,
            EventType.WHITE_WOLF_KILLED,
            EventType.WOLF_BEAUTY_CHARMED,
            EventType.NIGHTMARE_BLOCKED,
            EventType.GUARDIAN_WOLF_PROTECTED,
            EventType.RAVEN_MARKED,
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

    @staticmethod
    def _phase_value(event: Event) -> str:
        return str(getattr(event.phase, "value", event.phase))

    def _is_night_phase(self, event: Event) -> bool:
        return self._phase_value(event) == "night"

    @staticmethod
    def _is_daybreak_message(event: Event) -> bool:
        return event.event_type == EventType.MESSAGE and (event.data or {}).get("action") == "daybreak"

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

        if event.event_type == EventType.VOTE_INTENTION_SNAPSHOT:
            self._present_vote_intention(event)
            return True

        if event.event_type == EventType.BELIEF_SNAPSHOT:
            self._present_belief_snapshot(event)
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
        if viewer_id is not None:
            if event.event_type == EventType.PLAYER_DIED and self._is_night_phase(event):
                self._delayed_night_public_events.append(event)
                return
            if not self._is_night_phase(event) and not self._is_daybreak_message(event):
                self._flush_delayed_night_public_events()
            if self._is_night_action_event(event.event_type):
                self._present_private_night_action(event)
                return
            if event.event_type == EventType.PLAYER_SPEECH:
                self._present_live_speech(event)
                return
            if event.event_type == EventType.PLAYER_DISCUSSION:
                self._present_live_werewolf_discussion(event)
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

    def _flush_day_transition_buffers(self) -> None:
        """入昼或警长竞选前结清夜间/白天残留缓冲。"""
        self._flush_werewolf_discussion()
        self._flush_night_actions()
        self._flush_delayed_night_public_events()
        self._flush_discussion()
        self._flush_votes()

    def _flush_all_pending_buffers(self) -> None:
        """游戏结束等终态前强制输出全部缓冲，避免残留。"""
        self._flush_day_transition_buffers()

    def _handle_phase_change(self, event: Event) -> None:
        """处理阶段切换并输出视觉分隔符。"""
        tw = self._is_traditional_chinese()
        phase_value = str((event.data or {}).get("phase", ""))
        if phase_value == "night":
            # 入夜前刷新已缓冲内容（但不刷新狼人讨论）
            self._flush_discussion()
            self._flush_votes()

            round_num = event.data.get("round", 0)
            round_label = "輪" if tw else "轮"
            console.print()
            console.print("═" * 70, style="blue")
            console.print(
                f"                    🌙 第 {round_num} {round_label} - 黑夜 🌙",
                style="bold blue",
            )
            console.print("═" * 70, style="blue")
            console.print()
        elif phase_value.startswith("day"):
            self._flush_day_transition_buffers()

            round_num = event.data.get("round", 0)
            round_label = "輪" if tw else "轮"
            console.print()
            console.print("═" * 70, style="yellow")
            console.print(
                f"                    ☀️  第 {round_num} {round_label} - 白天 ☀️",
                style="bold yellow",
            )
            console.print("═" * 70, style="yellow")
            console.print()
        elif phase_value == "sheriff_election":
            self._flush_day_transition_buffers()

            round_num = event.data.get("round", 0)
            round_label = "輪" if tw else "轮"
            title = "警長競選" if tw else "警长竞选"
            console.print()
            console.print("═" * 70, style="gold1")
            console.print(
                f"                    🎖️  第 {round_num} {round_label} - {title} 🎖️",
                style="bold gold1",
            )
            console.print("═" * 70, style="gold1")
            console.print()

    def _handle_narrator_message(self, event: Event) -> None:
        """处理旁白类事件。"""
        if not event.data:
            console.print(event.message, style="dim italic")
            return

        action = event.data.get("action", "")
        tw = self._is_traditional_chinese()

        if action == "night_falls":
            console.print("🌙 天黑請閉眼..." if tw else "🌙 天黑请闭眼...", style="bold blue")
        elif action == "werewolves_wake":
            console.print()
            console.print("🐺 狼人，請睜眼..." if tw else "🐺 狼人，请睁眼...", style="bold red")
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
            console.print("🐺 狼人，請閉眼..." if tw else "🐺 狼人，请闭眼...", style="bold blue")
        elif action == "daybreak":
            console.print(
                "☀️  天亮了，所有人請睜眼..." if tw else "☀️  天亮了，所有人请睁眼...",
                style="bold yellow",
            )
            self._flush_delayed_night_public_events()
        else:
            console.print(event.message, style="dim italic")

    def _buffer_night_action(self, event: Event) -> None:
        """缓冲夜间行动以便分组展示。"""
        # 提取干净文案（若已有 emoji 则去掉）
        message = event.message
        for emoji in ["🛡️", "💊", "☠️", "🔮", "🐺", "💕", "🐺💋", "🐺⚪", "🐺🛡️", "🐦‍⬛"]:
            message = message.replace(emoji, "").strip()

        # 为行动配上 emoji
        if event.event_type == EventType.GUARD_PROTECTED:
            icon = "🛡️"
        elif event.event_type == EventType.WITCH_SAVED:
            icon = "💊"
        elif event.event_type in {EventType.WITCH_POISON_USED, EventType.WITCH_POISONED}:
            icon = "☠️"
        elif event.event_type == EventType.SEER_CHECKED:
            icon = "🔮"
        elif event.event_type == EventType.WEREWOLF_KILLED:
            icon = "🐺"
        elif event.event_type == EventType.LOVERS_LINKED:
            icon = "💕"
        elif event.event_type == EventType.WHITE_WOLF_KILLED:
            icon = "🐺⚪"
        elif event.event_type == EventType.WOLF_BEAUTY_CHARMED:
            icon = "🐺💋"
        elif event.event_type == EventType.NIGHTMARE_BLOCKED:
            icon = "🌑"
        elif event.event_type == EventType.GUARDIAN_WOLF_PROTECTED:
            icon = "🐺🛡️"
        elif event.event_type == EventType.RAVEN_MARKED:
            icon = "🐦‍⬛"
        else:
            icon = "  "

        self._night_actions.append(f"{icon} {message}")

    def _present_private_night_action(self, event: Event) -> None:
        """Show night information that is visible to the current human player."""
        console.print()
        console.print(f"🔒 私密夜间信息：{event.message}", style="cyan")

    def _flush_night_actions(self) -> None:
        """展示所有已缓冲的夜间行动。"""
        if not self._night_actions:
            return

        console.print()
        title = "─── 夜晚行動結果 ───" if self._is_traditional_chinese() else "─── 夜晚行动结果 ───"
        console.print(title, style="dim cyan")
        for action in self._night_actions:
            console.print(f"   {action}", style="cyan")
        console.print()

        self._night_actions = []

    def _flush_delayed_night_public_events(self) -> None:
        """在人类玩家视角下，把夜间公开结果延迟到离开夜晚后展示。"""
        if not self._delayed_night_public_events:
            return

        for event in self._delayed_night_public_events:
            self._present_death(event)
        self._delayed_night_public_events = []

    def _buffer_discussion(self, event: Event) -> None:
        """缓冲讨论消息以便分组展示。"""
        if event.data:
            from llm_werewolf.game_runtime.support.fallback_log import fallback_prefix_from_data

            player_name = event.data.get("player_name", "Unknown")
            speech = event.data.get("speech", "")
            prefix = fallback_prefix_from_data(event.data)
            self._discussion_messages.append(f"{prefix}{player_name}: {speech}")

    def _present_live_speech(self, event: Event) -> None:
        """人类玩家视角下实时展示公开发言，避免投票后整轮重复刷屏。"""
        if not event.data:
            console.print(event.message, style="cyan")
            return
        from llm_werewolf.game_runtime.support.fallback_log import fallback_prefix_from_data

        player_name = event.data.get("player_name", "Unknown")
        speech = event.data.get("speech", "")
        prefix = fallback_prefix_from_data(event.data)
        style = "bold yellow" if prefix else "cyan"
        console.print(f"\n💬 {prefix}{player_name}: {speech}", style=style)

    def _present_live_werewolf_discussion(self, event: Event) -> None:
        """人类狼人视角下实时展示已可见的狼队夜聊。"""
        if not event.data:
            console.print(event.message, style="red")
            return
        player_name = event.data.get("player_name", "Unknown")
        speech = event.data.get("speech", "")
        console.print(f"\n🐺 {player_name}: {speech}", style="red")

    def _buffer_werewolf_discussion(self, event: Event) -> None:
        """缓冲狼人讨论以便分组展示。"""
        if event.data:
            from llm_werewolf.game_runtime.support.fallback_log import fallback_prefix_from_data

            player_name = event.data.get("player_name", "Unknown")
            speech = event.data.get("speech", "")
            prefix = fallback_prefix_from_data(event.data)
            self._werewolf_discussion.append(f"🐺 {prefix}{player_name}: {speech}")

    def _flush_werewolf_discussion(self) -> None:
        """展示狼人讨论（仅在夜晚阶段调用）。"""
        if self._werewolf_discussion:
            console.print()
            panel = Panel(
                "\n".join(self._werewolf_discussion),
                title="狼人討論" if self._is_traditional_chinese() else "狼人讨论",
                border_style="red",
                padding=(1, 2),
            )
            console.print(panel)
            self._werewolf_discussion = []

    def _flush_discussion(self) -> None:
        """展示所有已缓冲的玩家发言。"""
        if self._discussion_messages:
            console.print()
            title = "💬 玩家發言" if self._is_traditional_chinese() else "💬 玩家发言"
            console.print(title, style="bold cyan")
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
        title = "🗳️  投票階段" if self._is_traditional_chinese() else "🗳️  投票阶段"
        console.print(title, style="bold yellow")
        console.print()

        # 构建投票汇总表
        tw = self._is_traditional_chinese()
        table = Table(show_header=True, header_style="bold yellow", box=None)
        table.add_column("排名", justify="center", width=6)
        table.add_column("候選人" if tw else "候选人", style="cyan", width=20)
        table.add_column("票數" if tw else "票数", justify="center", style="yellow", width=8)
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
        tw = self._is_traditional_chinese()
        title = "🎮 遊戲開始 🎮" if tw else "🎮 游戏开始 🎮"
        count_label = "玩家人數" if tw else "玩家人数"
        console.print()
        console.print("═" * 70, style="bold green")
        console.print(f"{title:^36}", style="bold green")
        console.print("═" * 70, style="bold green")
        if event.data:
            player_count = event.data.get("player_count", 0)
            console.print(f"\n📋 {count_label}：{player_count} 人\n", style="green")

    def _present_game_end(self, event: Event) -> None:
        """展示游戏结束。"""
        self._flush_all_pending_buffers()
        title = "🏆 遊戲結束 🏆" if self._is_traditional_chinese() else "🏆 游戏结束 🏆"
        console.print()
        console.print("═" * 70, style="bold magenta")
        console.print(f"{title:^36}", style="bold magenta")
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

    def _present_vote_intention(self, event: Event) -> None:
        """展示投票意向变化（上帝视角）。"""
        self._flush_discussion()
        console.print(f"📊 {event.message}", style="dim cyan")

    def _present_belief_snapshot(self, event: Event) -> None:
        """展示信念矩阵快照（上帝视角）。"""
        self._flush_discussion()
        console.print()
        panel = Panel(
            event.message,
            title="信念矩阵",
            border_style="magenta",
            padding=(0, 1),
        )
        console.print(panel)
        console.print()

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
