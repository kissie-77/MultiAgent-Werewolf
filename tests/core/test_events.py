"""core/events.py 模块的测试。"""

from llm_werewolf.core.types import Event, EventType
from llm_werewolf.core.events import EventLogger


class TestEventLogger:
    """EventLogger 类的测试。"""

    def test_initialization(self) -> None:
        """测试 EventLogger 初始化。"""
        logger = EventLogger()
        assert logger.events == []
        assert logger.get_event_count() == 0

    def test_log_event(self) -> None:
        """测试记录单个事件。"""
        logger = EventLogger()
        event = Event(
            event_type=EventType.GAME_STARTED,
            round_number=1,
            phase="setup",
            message="Game started",
        )

        logger.log_event(event)

        assert len(logger.events) == 1
        assert logger.events[0] == event
        assert logger.get_event_count() == 1

    def test_create_event(self) -> None:
        """测试创建并记录事件。"""
        logger = EventLogger()

        event = logger.create_event(
            event_type=EventType.GAME_STARTED,
            round_number=1,
            phase="setup",
            message="Game started with 6 players",
        )

        assert event is not None
        assert event.event_type == EventType.GAME_STARTED
        assert event.round_number == 1
        assert event.phase == "setup"
        assert event.message == "Game started with 6 players"
        assert len(logger.events) == 1
        assert logger.get_event_count() == 1

    def test_create_event_with_data(self) -> None:
        """测试创建带附加数据的事件。"""
        logger = EventLogger()

        event = logger.create_event(
            event_type=EventType.PLAYER_DIED,
            round_number=2,
            phase="night",
            message="Alice died",
            data={"player_id": "p1", "cause": "werewolf"},
        )

        assert event.data == {"player_id": "p1", "cause": "werewolf"}
        assert logger.get_event_count() == 1

    def test_create_event_with_visibility(self) -> None:
        """测试创建带可见性限制的事件。"""
        logger = EventLogger()

        event = logger.create_event(
            event_type=EventType.PLAYER_SPEECH,
            round_number=2,
            phase="night",
            message="Werewolves discuss",
            visible_to=["p1", "p2"],
        )

        assert event.visible_to == ["p1", "p2"]
        assert logger.get_event_count() == 1

    def test_get_events_for_player_public(self) -> None:
        """测试获取玩家的公开事件。"""
        logger = EventLogger()

        # 公开事件（无可见性限制）
        logger.create_event(
            event_type=EventType.GAME_STARTED,
            round_number=1,
            phase="setup",
            message="Game started",
        )

        events = logger.get_events_for_player("p1")
        assert len(events) == 1

    def test_get_events_for_player_private(self) -> None:
        """测试获取玩家的私有事件。"""
        logger = EventLogger()

        # 私有事件（仅 p1 和 p2 可见）
        logger.create_event(
            event_type=EventType.PLAYER_SPEECH,
            round_number=1,
            phase="night",
            message="Werewolf discussion",
            visible_to=["p1", "p2"],
        )

        # p1 应能看到
        events_p1 = logger.get_events_for_player("p1")
        assert len(events_p1) == 1

        # p3 不应看到
        events_p3 = logger.get_events_for_player("p3")
        assert len(events_p3) == 0

    def test_get_events_for_player_since_round(self) -> None:
        """测试获取玩家自指定回合起的事件。"""
        logger = EventLogger()

        logger.create_event(
            event_type=EventType.GAME_STARTED, round_number=1, phase="setup", message="Round 1"
        )
        logger.create_event(
            event_type=EventType.PHASE_CHANGED, round_number=2, phase="night", message="Round 2"
        )
        logger.create_event(
            event_type=EventType.PHASE_CHANGED, round_number=3, phase="day_discussion", message="Round 3"
        )

        # 获取第 2 回合起的事件
        events = logger.get_events_for_player("p1", since_round=2)
        assert len(events) == 2
        assert events[0].round_number == 2
        assert events[1].round_number == 3

    def test_get_events_for_players(self) -> None:
        """测试获取对整组玩家可见的事件。"""
        logger = EventLogger()

        logger.create_event(
            event_type=EventType.PLAYER_SPEECH,
            round_number=1,
            phase="night",
            message="Werewolf discussion",
            visible_to=["p1", "p2"],
        )
        logger.create_event(
            event_type=EventType.PLAYER_SPEECH,
            round_number=1,
            phase="night",
            message="Seer result",
            visible_to=["p1"],
        )

        events = logger.get_events_for_players(["p1", "p2"])
        assert len(events) == 1
        assert events[0].message == "Werewolf discussion"

    def test_get_recent_events(self) -> None:
        """测试获取最近事件。"""
        logger = EventLogger()

        # 添加 5 个事件
        for i in range(5):
            logger.create_event(
                event_type=EventType.PLAYER_DISCUSSION,
                round_number=1,
                phase="day_discussion",
                message=f"Message {i}",
            )

        # 获取最后 3 个事件
        recent = logger.get_recent_events(count=3)
        assert len(recent) == 3
        assert recent[0].message == "Message 2"
        assert recent[1].message == "Message 3"
        assert recent[2].message == "Message 4"

    def test_get_recent_events_more_than_available(self) -> None:
        """测试请求超过可用数量的最近事件。"""
        logger = EventLogger()

        # 添加 3 个事件
        for i in range(3):
            logger.create_event(
                event_type=EventType.PLAYER_DISCUSSION,
                round_number=1,
                phase="day_discussion",
                message=f"Message {i}",
            )

        # 请求 10 个事件，应返回全部 3 个
        recent = logger.get_recent_events(count=10)
        assert len(recent) == 3

    def test_get_events_by_type(self) -> None:
        """测试按类型获取事件。"""
        logger = EventLogger()

        logger.create_event(
            event_type=EventType.PLAYER_DIED, round_number=1, phase="night", message="Death 1"
        )
        logger.create_event(
            event_type=EventType.PLAYER_DISCUSSION,
            round_number=1,
            phase="day_discussion",
            message="Discussion",
        )
        logger.create_event(
            event_type=EventType.PLAYER_DIED, round_number=2, phase="night", message="Death 2"
        )

        # 获取所有死亡事件
        death_events = logger.get_events_by_type(EventType.PLAYER_DIED)
        assert len(death_events) == 2
        assert death_events[0].message == "Death 1"
        assert death_events[1].message == "Death 2"

    def test_get_events_by_type_with_round(self) -> None:
        """测试按类型和回合获取事件。"""
        logger = EventLogger()

        logger.create_event(
            event_type=EventType.PLAYER_DIED, round_number=1, phase="night", message="Death R1"
        )
        logger.create_event(
            event_type=EventType.PLAYER_DIED, round_number=2, phase="night", message="Death R2"
        )
        logger.create_event(
            event_type=EventType.PLAYER_DISCUSSION,
            round_number=1,
            phase="day_discussion",
            message="Discussion",
        )

        # 仅获取第 1 回合的死亡事件
        death_events_r1 = logger.get_events_by_type(EventType.PLAYER_DIED, round_number=1)
        assert len(death_events_r1) == 1
        assert death_events_r1[0].message == "Death R1"

    def test_clear_events(self) -> None:
        """测试清空所有事件。"""
        logger = EventLogger()

        # 添加一些事件
        for i in range(5):
            logger.create_event(
                event_type=EventType.PLAYER_DISCUSSION,
                round_number=1,
                phase="day_discussion",
                message=f"Message {i}",
            )

        assert logger.get_event_count() == 5

        # 清空事件
        logger.clear_events()

        assert logger.get_event_count() == 0
        assert len(logger.events) == 0

    def test_get_event_count(self) -> None:
        """测试获取事件数量。"""
        logger = EventLogger()

        assert logger.get_event_count() == 0

        logger.create_event(
            event_type=EventType.GAME_STARTED, round_number=1, phase="setup", message="Start"
        )
        assert logger.get_event_count() == 1

        logger.create_event(
            event_type=EventType.PHASE_CHANGED, round_number=1, phase="night", message="Night"
        )
        assert logger.get_event_count() == 2

    def test_multiple_operations(self) -> None:
        """测试连续执行多项操作。"""
        logger = EventLogger()

        # 创建事件
        for i in range(10):
            logger.create_event(
                event_type=EventType.PLAYER_DISCUSSION if i % 2 == 0 else EventType.PLAYER_DIED,
                round_number=i // 3 + 1,
                phase="day_discussion" if i % 2 == 0 else "night",
                message=f"Event {i}",
            )

        # 测试事件数量
        assert logger.get_event_count() == 10

        # 测试按类型过滤
        discussions = logger.get_events_by_type(EventType.PLAYER_DISCUSSION)
        assert len(discussions) == 5

        deaths = logger.get_events_by_type(EventType.PLAYER_DIED)
        assert len(deaths) == 5

        # 测试按回合过滤
        round_1_events = logger.get_events_for_player("p1", since_round=2)
        assert all(e.round_number >= 2 for e in round_1_events)

        # 测试最近事件
        recent = logger.get_recent_events(count=5)
        assert len(recent) == 5
        assert recent[-1].message == "Event 9"
