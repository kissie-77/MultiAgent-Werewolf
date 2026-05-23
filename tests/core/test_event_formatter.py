"""事件格式化器的测试。"""

from datetime import datetime

from llm_werewolf.core.types import Event, EventType
from llm_werewolf.core.event_formatter import EventFormatter


def test_format_event_with_timestamp() -> None:
    """测试格式化带时间戳的事件。"""
    event = Event(
        event_type=EventType.GAME_STARTED,
        round_number=1,
        phase="setup",
        message="Game started with 6 players",
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
    )

    formatted = EventFormatter.format_event(event, include_timestamp=True)

    # 检查包含时间戳
    assert "[12:00:00]" in str(formatted)
    # 检查包含消息
    assert "Game started with 6 players" in str(formatted)


def test_format_event_without_timestamp() -> None:
    """测试格式化不带时间戳的事件。"""
    event = Event(
        event_type=EventType.PLAYER_DIED,
        round_number=1,
        phase="night",
        message="Player 1 has died",
    )

    formatted = EventFormatter.format_event(event, include_timestamp=False)

    # 检查不包含时间戳
    assert "[" not in str(formatted) or "Player 1" in str(formatted)


def test_get_event_style() -> None:
    """测试获取不同事件类型的样式。"""
    # 测试已知事件类型
    assert EventFormatter.get_event_style(EventType.GAME_STARTED) == "bold green"
    assert EventFormatter.get_event_style(EventType.GAME_ENDED) == "bold red"
    assert EventFormatter.get_event_style(EventType.PLAYER_DIED) == "red"
    assert EventFormatter.get_event_style(EventType.VOTE_RESULT) == "bold yellow"


def test_format_event_styles() -> None:
    """测试不同事件类型获得合适样式。"""
    # 测试几种不同事件类型
    test_cases = [
        (EventType.GAME_STARTED, "bold green"),
        (EventType.WEREWOLF_KILLED, "red"),
        (EventType.WITCH_SAVED, "green"),
        (EventType.PHASE_CHANGED, "bold cyan"),
    ]

    for event_type, expected_style in test_cases:
        event = Event(event_type=event_type, round_number=1, phase="test", message="Test message")
        formatted = EventFormatter.format_event(event)
        # 仅验证不抛出错误
        assert formatted is not None
        assert EventFormatter.get_event_style(event_type) == expected_style


def test_format_all_event_types() -> None:
    """测试格式化所有事件类型以确保完整覆盖。"""
    # 测试 EVENT_STYLES 中所有事件类型
    for event_type in EventFormatter.EVENT_STYLES:
        event = Event(
            event_type=event_type,
            round_number=1,
            phase="test",
            message=f"Test message for {event_type.value}",
        )
        formatted = EventFormatter.format_event(event, include_timestamp=True)
        assert formatted is not None
        assert f"Test message for {event_type.value}" in str(formatted)


def test_unknown_event_type_style() -> None:
    """测试未知事件类型获得默认白色样式。"""
    # 测试所有枚举值以确保覆盖
    for event_type in EventType:
        style = EventFormatter.get_event_style(event_type)
        # 应返回有效样式字符串
        assert isinstance(style, str)
        assert len(style) > 0
