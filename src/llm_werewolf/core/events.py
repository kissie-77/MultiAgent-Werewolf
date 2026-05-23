from llm_werewolf.core.types import Event, EventType
from llm_werewolf.core.types.enums import GamePhase


class EventLogger:
    """记录并管理游戏事件。"""

    def __init__(self) -> None:
        """初始化事件记录器。"""
        self.events: list[Event] = []

    def log_event(self, event: Event) -> None:
        """记录一条事件。

        Args:
            event: 待记录的事件。
        """
        self.events.append(event)

    def create_event(
        self,
        event_type: EventType,
        round_number: int,
        phase: GamePhase,
        message: str,
        data: dict | None = None,
        visible_to: list[str] | None = None,
    ) -> Event:
        """创建并记录新事件。

        Args:
            event_type: 事件类型。
            round_number: 当前回合数。
            phase: 当前游戏阶段。
            message: 事件消息。
            data: 附加事件数据。
            visible_to: 可查看该事件的玩家 ID 列表。

        Returns:
            Event: 创建的事件。
        """
        event = Event(
            event_type=event_type,
            round_number=round_number,
            phase=phase,
            message=message,
            data=data or {},
            visible_to=visible_to,
        )
        self.log_event(event)
        return event

    def get_events_for_player(self, player_id: str, since_round: int | None = None) -> list[Event]:
        """获取指定玩家可见的所有事件。

        Args:
            player_id: 玩家 ID。
            since_round: 仅返回该回合及之后的事件。

        Returns:
            list[Event]: 可见事件列表。
        """
        events = [e for e in self.events if e.is_visible_to(player_id)]

        if since_round is not None:
            events = [e for e in events if e.round_number >= since_round]

        return events

    def get_events_for_players(
        self, player_ids: list[str], since_round: int | None = None
    ) -> list[Event]:
        """获取一组玩家均可见的所有事件。"""
        shared_events = [
            event for event in self.events if all(event.is_visible_to(player_id) for player_id in player_ids)
        ]

        if since_round is not None:
            shared_events = [event for event in shared_events if event.round_number >= since_round]

        return shared_events

    def get_recent_events(self, count: int = 10) -> list[Event]:
        """获取最近的事件。

        Args:
            count: 要获取的事件数量。

        Returns:
            list[Event]: 最近的事件。
        """
        return self.events[-count:]

    def get_events_by_type(
        self, event_type: EventType, round_number: int | None = None
    ) -> list[Event]:
        """获取指定类型的所有事件。

        Args:
            event_type: 要筛选的事件类型。
            round_number: 可选，按回合数筛选。

        Returns:
            list[Event]: 匹配的事件列表。
        """
        events = [e for e in self.events if e.event_type == event_type]

        if round_number is not None:
            events = [e for e in events if e.round_number == round_number]

        return events

    def clear_events(self) -> None:
        """清空所有事件。"""
        self.events.clear()

    def get_event_count(self) -> int:
        """获取事件总数。

        Returns:
            int: 已记录的事件数量。
        """
        return len(self.events)
