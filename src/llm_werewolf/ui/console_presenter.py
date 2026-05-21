"""Console presenter for beautified game output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.console import Console

from llm_werewolf.core.types import Event, EventType

if TYPE_CHECKING:
    from llm_werewolf.core.locale import Locale

console = Console()


class ConsolePresenter:
    """Presents game events in a beautified console format with proper pacing."""

    def __init__(self, locale: Locale) -> None:
        """Initialize the console presenter.

        Args:
            locale: Locale instance for localized strings.
        """
        self.locale = locale
        self._last_phase = ""
        self._last_round = -1
        self._night_actions: list[str] = []
        self._vote_buffer: dict[str, list[str]] = {}  # target_name -> [voters]
        self._in_voting_phase = False
        self._discussion_messages: list[str] = []
        self._werewolf_discussion: list[str] = []

    def _is_night_action_event(self, event_type: EventType) -> bool:
        """Check if event type is a night action that should be buffered.

        Args:
            event_type: The event type to check.

        Returns:
            bool: True if event should be buffered.
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
        """Check if event type is sheriff-related.

        Args:
            event_type: The event type to check.

        Returns:
            bool: True if sheriff-related event.
        """
        return event_type in {
            EventType.SHERIFF_CAMPAIGN_STARTED,
            EventType.SHERIFF_CANDIDATE_SPEECH,
            EventType.SHERIFF_VOTE_CAST,
            EventType.SHERIFF_ELECTED,
            EventType.SHERIFF_BADGE_TRANSFERRED,
        }

    def _handle_special_events(self, event: Event) -> bool:
        """Handle special event types and return whether event was handled.

        Args:
            event: The event to handle.

        Returns:
            bool: True if event was handled, False otherwise.
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
        """Handle game lifecycle events (start, end).

        Args:
            event: The event to handle.

        Returns:
            bool: True if event was handled, False otherwise.
        """
        if event.event_type == EventType.GAME_STARTED:
            self._present_game_start(event)
            return True
        if event.event_type == EventType.GAME_ENDED:
            self._present_game_end(event)
            return True
        return False

    def _handle_player_events(self, event: Event) -> bool:
        """Handle player-related events (speech, death, elimination).

        Args:
            event: The event to handle.

        Returns:
            bool: True if event was handled, False otherwise.
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
        """Handle voting-related events.

        Args:
            event: The event to handle.

        Returns:
            bool: True if event was handled, False otherwise.
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
        """Present an event with appropriate formatting.

        Args:
            event: The event to present.
            viewer_id: If set, only show events visible to this player (god view when None).
        """
        if viewer_id is not None and not event.is_visible_to(viewer_id):
            return
        if viewer_id is not None and self._is_night_action_event(event.event_type):
            return

        # Handle phase transitions
        if event.event_type == EventType.PHASE_CHANGED:
            self._handle_phase_change(event)
        # Handle different event categories
        elif self._handle_game_lifecycle_events(event):
            pass  # Already handled
        elif event.event_type == EventType.MESSAGE:
            self._handle_narrator_message(event)
        elif event.event_type == EventType.ROLE_ACTING:
            pass  # Buffer night actions
        elif self._is_night_action_event(event.event_type):
            self._buffer_night_action(event)
        elif (
            self._handle_player_events(event)
            or self._handle_voting_events(event)
            or self._handle_special_events(event)
        ):
            pass  # Already handled
        else:
            # Default: print with appropriate style
            style = self._get_event_style(event.event_type)
            console.print(event.message, style=style)

    def _handle_phase_change(self, event: Event) -> None:
        """Handle phase transition with visual separators."""
        if event.data and event.data.get("phase") == "night":
            # Flush any buffered content before night (but NOT werewolf discussion)
            self._flush_discussion()
            self._flush_votes()

            round_num = event.data.get("round", 0)
            console.print()
            console.print("═" * 70, style="blue")
            console.print(f"                    🌙 第 {round_num} 輪 - 黑夜 🌙", style="bold blue")
            console.print("═" * 70, style="blue")
            console.print()
        elif event.data and event.data.get("phase") == "day":
            # Flush night actions and werewolf discussion before day
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
        """Handle narrator messages."""
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
            # Flush werewolf discussion before voting
            self._flush_werewolf_discussion()
            console.print()
            console.print("🐺 狼人正在选择目标...", style="dim red")
        elif action == "werewolves_sleep":
            # Flush night actions when werewolves sleep
            self._flush_night_actions()
            console.print()
            console.print("🐺 狼人，請閉眼...", style="bold blue")
        elif action == "daybreak":
            console.print("☀️  天亮了，所有人請睜眼...", style="bold yellow")
        else:
            console.print(event.message, style="dim italic")

    def _buffer_night_action(self, event: Event) -> None:
        """Buffer night actions for grouped display."""
        # Extract clean message (remove emoji if already present)
        message = event.message
        for emoji in ["🛡️", "💊", "☠️", "🔮", "🐺", "💕", "🐺💋"]:
            message = message.replace(emoji, "").strip()

        # Format action with emoji
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
        """Display all buffered night actions."""
        if not self._night_actions:
            return

        console.print()
        console.print("─── 夜晚行動結果 ───", style="dim cyan")
        for action in self._night_actions:
            console.print(f"   {action}", style="cyan")
        console.print()

        self._night_actions = []

    def _buffer_discussion(self, event: Event) -> None:
        """Buffer discussion messages for grouped display."""
        if event.data:
            player_name = event.data.get("player_name", "Unknown")
            speech = event.data.get("speech", "")
            self._discussion_messages.append(f"{player_name}: {speech}")

    def _buffer_werewolf_discussion(self, event: Event) -> None:
        """Buffer werewolf discussion for grouped display."""
        if event.data:
            player_name = event.data.get("player_name", "Unknown")
            speech = event.data.get("speech", "")
            self._werewolf_discussion.append(f"🐺 {player_name}: {speech}")

    def _flush_werewolf_discussion(self) -> None:
        """Display werewolf discussion (only called during night phase)."""
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
        """Display all buffered player discussion messages."""
        if self._discussion_messages:
            console.print()
            console.print("💬 玩家發言", style="bold cyan")
            console.print("─" * 70, style="dim")
            for msg in self._discussion_messages:
                console.print(f"   {msg}", style="cyan")
            console.print()
            self._discussion_messages = []

    def _buffer_vote(self, event: Event) -> None:
        """Buffer vote for grouped display."""
        if event.data:
            target_name = event.data.get("target_name", "Unknown")
            voter_name = event.data.get("voter_name", "Unknown")
            if target_name not in self._vote_buffer:
                self._vote_buffer[target_name] = []
            self._vote_buffer[target_name].append(voter_name)

    def _flush_votes(self) -> None:
        """Display all buffered votes in a table."""
        if not self._vote_buffer:
            return

        # First flush any discussion
        self._flush_discussion()

        console.print()
        console.print("🗳️  投票階段", style="bold yellow")
        console.print()

        # Create vote summary table
        table = Table(show_header=True, header_style="bold yellow", box=None)
        table.add_column("排名", justify="center", width=6)
        table.add_column("候選人", style="cyan", width=20)
        table.add_column("票數", justify="center", style="yellow", width=8)
        table.add_column("投票者", style="dim")

        # Sort by vote count
        sorted_votes = sorted(self._vote_buffer.items(), key=lambda x: len(x[1]), reverse=True)

        # Add rank emoji
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
        """Present game start."""
        console.print()
        console.print("═" * 70, style="bold green")
        console.print("                      🎮 遊戲開始 🎮", style="bold green")
        console.print("═" * 70, style="bold green")
        if event.data:
            player_count = event.data.get("player_count", 0)
            console.print(f"\n📋 玩家人數：{player_count} 人\n", style="green")

    def _present_game_end(self, event: Event) -> None:
        """Present game end."""
        console.print()
        console.print("═" * 70, style="bold magenta")
        console.print("                      🏆 遊戲結束 🏆", style="bold magenta")
        console.print("═" * 70, style="bold magenta")
        console.print()
        console.print(event.message, style="bold magenta")
        console.print()

    def _present_death(self, event: Event) -> None:
        """Present player death."""
        console.print(f"💀 {event.message}", style="bold red")

    def _present_elimination(self, event: Event) -> None:
        """Present player elimination."""
        console.print()
        console.print(f"⚰️  {event.message}", style="bold red")
        console.print()

    def _present_hunter_revenge(self, event: Event) -> None:
        """Present hunter revenge."""
        console.print(f"🏹 {event.message}", style="bold yellow")

    def _present_sheriff_event(self, event: Event) -> None:
        """Present sheriff-related events."""
        console.print(f"🎖️  {event.message}", style="gold1")

    def _present_role_reveal(self, event: Event) -> None:
        """Present role reveal."""
        console.print(f"🎭 {event.message}", style="bold magenta")

    def _get_event_style(self, event_type: EventType) -> str:
        """Get style for event type."""
        styles = {
            EventType.ERROR: "bold red",
            EventType.PLAYER_DIED: "red",
            EventType.PLAYER_ELIMINATED: "bold red",
            EventType.HUNTER_REVENGE: "yellow",
            EventType.VOTE_RESULT: "yellow",
        }
        return styles.get(event_type, "white")
