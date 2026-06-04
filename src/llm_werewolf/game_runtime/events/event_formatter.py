"""在 CLI 与 TUI 间统一事件展示格式。"""

from typing import ClassVar

from rich.text import Text

from llm_werewolf.game_runtime.types import Event, EventType


class EventFormatter:
    """以一致样式格式化游戏事件以供展示。"""

    # 事件类型到样式的映射（CLI 与 TUI 共用）
    EVENT_STYLES: ClassVar[dict[EventType, str]] = {
        EventType.GAME_STARTED: "bold green",
        EventType.GAME_ENDED: "bold red",
        EventType.PHASE_CHANGED: "bold cyan",
        EventType.ROUND_STARTED: "bold blue",
        EventType.PLAYER_DIED: "red",
        EventType.PLAYER_REVIVED: "green",
        EventType.ROLE_REVEALED: "magenta",
        EventType.ROLE_ACTING: "dim cyan",
        EventType.WEREWOLF_KILLED: "red",
        EventType.WITCH_SAVED: "green",
        EventType.WITCH_POISON_USED: "red",
        EventType.WITCH_POISONED: "red",
        EventType.SEER_CHECKED: "blue",
        EventType.GUARD_PROTECTED: "green",
        EventType.WHITE_WOLF_KILLED: "red",
        EventType.WOLF_BEAUTY_CHARMED: "magenta",
        EventType.NIGHTMARE_BLOCKED: "yellow",
        EventType.GUARDIAN_WOLF_PROTECTED: "green",
        EventType.RAVEN_MARKED: "yellow",
        EventType.LOVERS_LINKED: "magenta",
        EventType.LOVER_DIED: "red",
        EventType.HUNTER_REVENGE: "yellow",
        EventType.KNIGHT_DUEL: "yellow",
        EventType.VOTE_CAST: "yellow",
        EventType.VOTE_RESULT: "bold yellow",
        EventType.VOTE_INTENTION_SNAPSHOT: "dim yellow",
        EventType.PLAYER_ELIMINATED: "bold red",
        EventType.SHERIFF_CAMPAIGN_STARTED: "bold gold1",
        EventType.SHERIFF_CANDIDATE_SPEECH: "gold1",
        EventType.SHERIFF_VOTE_CAST: "yellow",
        EventType.SHERIFF_ELECTED: "bold gold1",
        EventType.SHERIFF_TIE: "yellow",
        EventType.SHERIFF_BADGE_TRANSFERRED: "gold1",
        EventType.SHERIFF_BADGE_TORN: "dim gold1",
        EventType.PLAYER_SPEECH: "cyan",
        EventType.PLAYER_DISCUSSION: "blue",
        EventType.MESSAGE: "dim italic",
        EventType.ERROR: "bold red",
    }

    @classmethod
    def format_event(cls, event: Event, include_timestamp: bool = True) -> Text:
        """将事件格式化为带合适样式的 Rich Text。

        Args:
            event: 待格式化的事件。
            include_timestamp: 是否在输出中包含时间戳。

        Returns:
            Text: 格式化后的 Rich Text 对象。
        """
        text = Text()

        # 按需添加时间戳
        if include_timestamp:
            time_str = event.timestamp.strftime("%H:%M:%S")
            text.append(f"[{time_str}] ", style="dim")

        # 获取该事件类型的样式（未找到则默认为 white）
        style = cls.EVENT_STYLES.get(event.event_type, "white")

        # 以对应样式追加消息
        text.append(event.message, style=style)

        return text

    @classmethod
    def get_event_style(cls, event_type: EventType) -> str:
        """获取指定事件类型的样式。

        Args:
            event_type: 事件类型。

        Returns:
            str: 用于 Rich 格式化的样式字符串。
        """
        return cls.EVENT_STYLES.get(event_type, "white")
