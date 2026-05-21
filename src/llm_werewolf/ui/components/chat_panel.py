from typing import Any
import datetime

from rich.text import Text
from textual.widgets import RichLog

from llm_werewolf.core.types import EventType
from llm_werewolf.core.events import Event
from llm_werewolf.core.event_formatter import EventFormatter


class ChatPanel(RichLog):
    """Widget displaying the game chat/event history."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the chat panel."""
        super().__init__(*args, **kwargs)
        self.events: list[Event] = []
        self._streaming_line_count: int = 0

        # Buffers for grouped display
        self._night_actions: list[tuple[EventType, str]] = []
        self._discussion_messages: list[str] = []
        self._werewolf_discussion: list[str] = []
        self._vote_buffer: dict[str, list[str]] = {}  # target_name -> [voters]
        self._last_phase = ""

    def add_event(self, event: Event) -> None:
        """Add an event to the chat history.

        Args:
            event: The event to add.
        """
        self.events.append(event)
        self.display_event(event)

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
            text = Text(f"🏹 {event.message}", style="bold yellow")
            self.write(text)
            return True

        if self._is_sheriff_event(event.event_type):
            text = Text(f"🎖️  {event.message}", style="gold1")
            self.write(text)
            return True

        if event.event_type == EventType.ROLE_REVEALED:
            text = Text(f"🎭 {event.message}", style="bold magenta")
            self.write(text)
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

    def display_event(self, event: Event, viewer_id: str | None = None) -> None:
        """Display an event in the chat panel with grouped formatting.

        Args:
            event: The event to display.
            viewer_id: If set, filter to events visible to this player.
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
            # Default: use centralized formatter
            text = EventFormatter.format_event(event, include_timestamp=True)
            self.write(text)

    def _handle_phase_change(self, event: Event) -> None:
        """Handle phase transition with visual separators."""
        if event.data and event.data.get("phase") == "night":
            # Flush any buffered content before night
            self._flush_discussion()
            self._flush_votes()

            round_num = event.data.get("round", 0)
            self.write("")
            self.write(Text("═" * 70, style="blue"))
            self.write(
                Text(f"                    🌙 第 {round_num} 輪 - 黑夜 🌙", style="bold blue")
            )
            self.write(Text("═" * 70, style="blue"))
            self.write("")
        elif event.data and event.data.get("phase") == "day":
            # Flush night actions before day
            self._flush_night_actions()

            round_num = event.data.get("round", 0)
            self.write("")
            self.write(Text("═" * 70, style="yellow"))
            self.write(
                Text(f"                    ☀️  第 {round_num} 輪 - 白天 ☀️", style="bold yellow")
            )
            self.write(Text("═" * 70, style="yellow"))
            self.write("")

    def _handle_narrator_message(self, event: Event) -> None:
        """Handle narrator messages."""
        if not event.data:
            text = Text(event.message, style="dim italic")
            self.write(text)
            return

        action = event.data.get("action", "")

        if action == "night_falls":
            self.write(Text("🌙 天黑請閉眼...", style="bold blue"))
        elif action == "werewolves_wake":
            self.write("")
            self.write(Text("🐺 狼人，請睜眼...", style="bold red"))
            self.write("")
        elif action == "werewolves_vote":
            # Flush werewolf discussion before voting
            self._flush_werewolf_discussion()
            self.write("")
            self.write(Text("🐺 狼人正在选择目标...", style="dim red"))
        elif action == "werewolves_sleep":
            # Flush night actions when werewolves sleep
            self._flush_night_actions()
            self.write("")
            self.write(Text("🐺 狼人，請閉眼...", style="bold blue"))
        elif action == "daybreak":
            self.write(Text("☀️  天亮了，所有人請睜眼...", style="bold yellow"))
        else:
            text = Text(event.message, style="dim italic")
            self.write(text)

    def _buffer_night_action(self, event: Event) -> None:
        """Buffer night actions for grouped display."""
        self._night_actions.append((event.event_type, event.message))

    def _flush_night_actions(self) -> None:
        """Display all buffered night actions."""
        if not self._night_actions:
            return

        self.write("")
        self.write(Text("─── 夜晚行動結果 ───", style="dim cyan"))

        for event_type, message in self._night_actions:
            # Remove emoji if already present
            clean_msg = message
            for emoji in ["🛡️", "💊", "☠️", "🔮", "🐺", "💕", "🐺💋"]:
                clean_msg = clean_msg.replace(emoji, "").strip()

            # Add emoji based on event type
            if event_type == EventType.GUARD_PROTECTED:
                icon = "🛡️"
            elif event_type == EventType.WITCH_SAVED:
                icon = "💊"
            elif event_type == EventType.WITCH_POISONED:
                icon = "☠️"
            elif event_type == EventType.SEER_CHECKED:
                icon = "🔮"
            elif event_type == EventType.WEREWOLF_KILLED:
                icon = "🐺"
            elif event_type == EventType.LOVERS_LINKED:
                icon = "💕"
            else:
                icon = "  "

            self.write(Text(f"   {icon} {clean_msg}", style="cyan"))

        self.write("")
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
            self._werewolf_discussion.append(f"{player_name}: {speech}")

    def _flush_werewolf_discussion(self) -> None:
        """Display werewolf discussion (only called during night phase)."""
        if self._werewolf_discussion:
            self.write("")
            self.write(
                Text("┌─ 狼人討論 ─────────────────────────────────────────────┐", style="red")
            )
            for msg in self._werewolf_discussion:
                self.write(Text(f"│ 🐺 {msg}", style="red"))
            self.write(
                Text("└────────────────────────────────────────────────────────┘", style="red")
            )
            self._werewolf_discussion = []

    def _flush_discussion(self) -> None:
        """Display all buffered player discussion messages."""
        if self._discussion_messages:
            self.write("")
            self.write(Text("💬 玩家發言", style="bold cyan"))
            self.write(Text("─" * 70, style="dim"))
            for msg in self._discussion_messages:
                self.write(Text(f"   {msg}", style="cyan"))
            self.write("")
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
        """Display all buffered votes."""
        if not self._vote_buffer:
            return

        # First flush any discussion
        self._flush_discussion()

        self.write("")
        self.write(Text("🗳️  投票階段", style="bold yellow"))
        self.write("")

        # Sort by vote count
        sorted_votes = sorted(self._vote_buffer.items(), key=lambda x: len(x[1]), reverse=True)

        # Add rank emoji
        rank_emoji = {0: "🥇", 1: "🥈", 2: "🥉"}

        for idx, (target, voters) in enumerate(sorted_votes):
            vote_count = len(voters)
            voters_str = ", ".join(voters)
            rank = rank_emoji.get(idx, "  ")

            text = Text()
            text.append(f" {rank} ", style="bold yellow")
            text.append(f"{target} ", style="cyan")
            text.append(f"({vote_count}票)", style="yellow")
            text.append(f" ← {voters_str}", style="dim")
            self.write(text)

        self.write("")
        self._vote_buffer = {}

    def _present_game_start(self, event: Event) -> None:
        """Present game start."""
        self.write("")
        self.write(Text("═" * 70, style="bold green"))
        self.write(Text("                      🎮 遊戲開始 🎮", style="bold green"))
        self.write(Text("═" * 70, style="bold green"))
        if event.data:
            player_count = event.data.get("player_count", 0)
            self.write(Text(f"📋 玩家人數：{player_count} 人", style="green"))
        self.write("")

    def _present_game_end(self, event: Event) -> None:
        """Present game end."""
        self.write("")
        self.write(Text("═" * 70, style="bold magenta"))
        self.write(Text("                      🏆 遊戲結束 🏆", style="bold magenta"))
        self.write(Text("═" * 70, style="bold magenta"))
        self.write("")
        self.write(Text(event.message, style="bold magenta"))
        self.write("")

    def _present_death(self, event: Event) -> None:
        """Present player death."""
        self.write(Text(f"💀 {event.message}", style="bold red"))

    def _present_elimination(self, event: Event) -> None:
        """Present player elimination."""
        self.write("")
        self.write(Text(f"⚰️  {event.message}", style="bold red"))
        self.write("")

    def add_system_message(self, message: str) -> None:
        """Add a system message to the chat.

        Args:
            message: The message to add.
        """
        text = Text()
        text.append("i  ", style="bold cyan")
        text.append(message, style="italic cyan")
        self.write(text)

    def add_player_message(self, player_name: str, message: str) -> None:
        """Add a player message to the chat.

        Args:
            player_name: Name of the player.
            message: The message content.
        """
        text = Text()
        text.append(f"{player_name}: ", style="bold")
        text.append(message)
        self.write(text)

    def clear_history(self) -> None:
        """Clear the chat history."""
        self.events.clear()
        self.clear()

    def start_streaming_message(self, player_name: str, prefix: str = "") -> None:
        """Start a streaming message display.

        Args:
            player_name: Name of the player speaking.
            prefix: Optional prefix to display before the streaming content.
        """
        text = Text()
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        text.append(f"[{time_str}] ", style="dim")

        if prefix:
            text.append(prefix, style="cyan")
            text.append(" ")

        text.append(f"{player_name}: ", style="bold cyan")
        self.write(text)
        self._streaming_line_count = 1

    def update_streaming_message(self, chunk: str) -> None:
        """Update the current streaming message with a new chunk.

        Args:
            chunk: New text chunk to append.
        """
        # Remove the last line(s) added by streaming
        if self._streaming_line_count > 0:
            # RichLog doesn't have a direct way to remove lines, so we append chunks
            # We'll use a simpler approach: just append the chunk as plain text
            text = Text(chunk, style="cyan")
            self.write(text, scroll_end=True)

    def finish_streaming_message(self) -> None:
        """Finish the streaming message."""
        self._streaming_line_count = 0
