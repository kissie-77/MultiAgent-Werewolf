"""ConsolePresenter event rendering tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.types import Event, EventType, GamePhase
from llm_werewolf.ui.console_presenter import ConsolePresenter


def _event(
    event_type: EventType,
    message: str = "event message",
    *,
    phase: GamePhase = GamePhase.DAY_DISCUSSION,
    round_number: int = 1,
    data: dict | None = None,
    visible_to: list[str] | None = None,
) -> Event:
    return Event(
        event_type=event_type,
        phase=phase,
        round_number=round_number,
        message=message,
        data=data or {},
        visible_to=visible_to,
    )


@pytest.fixture
def presenter() -> ConsolePresenter:
    return ConsolePresenter(Locale("zh-CN"))


@pytest.fixture
def mock_print():
    with patch("llm_werewolf.ui.console_presenter.console.print") as mocked:
        yield mocked


def test_present_event_skips_invisible_for_viewer(presenter: ConsolePresenter, mock_print) -> None:
    event = _event(EventType.MESSAGE, visible_to=["player_2"])
    presenter.present_event(event, viewer_id="player_1")
    mock_print.assert_not_called()


def test_present_event_skips_private_night_action_for_viewer(
    presenter: ConsolePresenter, mock_print
) -> None:
    event = _event(
        EventType.SEER_CHECKED,
        phase=GamePhase.NIGHT,
        visible_to=["player_2"],
    )
    presenter.present_event(event, viewer_id="player_1")
    mock_print.assert_not_called()


def test_human_viewer_sees_own_private_night_action(
    presenter: ConsolePresenter, mock_print
) -> None:
    event = _event(
        EventType.SEER_CHECKED,
        message="预言家查验：玩家2 是好人",
        phase=GamePhase.NIGHT,
        visible_to=["player_1"],
    )

    presenter.present_event(event, viewer_id="player_1")

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "私密夜间信息" in rendered
    assert "预言家查验" in rendered


def test_human_viewer_delays_public_night_death_until_daybreak(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(
            EventType.PLAYER_DIED,
            message="玩家4 被狼人杀害",
            phase=GamePhase.NIGHT,
        ),
        viewer_id="player_1",
    )

    mock_print.assert_not_called()

    presenter.present_event(
        _event(
            EventType.MESSAGE,
            message="☀️ 天亮了，所有人请睁眼...",
            phase=GamePhase.DAY_DISCUSSION,
            data={"action": "daybreak"},
        ),
        viewer_id="player_1",
    )

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "天亮了" in rendered
    assert "玩家4 被狼人杀害" in rendered
    assert rendered.index("天亮了") < rendered.index("玩家4 被狼人杀害")


def test_human_viewer_flushes_night_death_before_sheriff_event(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(EventType.PLAYER_DIED, message="玩家4 被狼人杀害", phase=GamePhase.NIGHT),
        viewer_id="player_1",
    )

    presenter.present_event(
        _event(
            EventType.SHERIFF_CAMPAIGN_STARTED,
            message="警长选举开始",
            phase=GamePhase.SHERIFF_ELECTION,
        ),
        viewer_id="player_1",
    )

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "玩家4 被狼人杀害" in rendered
    assert "警长选举开始" in rendered
    assert rendered.index("玩家4 被狼人杀害") < rendered.index("警长选举开始")


def test_present_event_skips_wolf_discussion_for_villager_viewer(
    presenter: ConsolePresenter, mock_print
) -> None:
    event = _event(
        EventType.PLAYER_DISCUSSION,
        message="wolf night chat",
        phase=GamePhase.NIGHT,
        data={"player_name": "狼人1", "speech": "今晚刀4号"},
        visible_to=["player_2", "player_3"],
    )

    presenter.present_event(event, viewer_id="player_1")

    mock_print.assert_not_called()


def test_present_event_skips_wolf_narration_for_villager_viewer(
    presenter: ConsolePresenter, mock_print
) -> None:
    event = _event(
        EventType.MESSAGE,
        message="🐺 狼人请睁眼，请讨论并选择目标...",
        phase=GamePhase.NIGHT,
        data={"action": "werewolves_wake"},
        visible_to=["player_2", "player_3"],
    )

    presenter.present_event(event, viewer_id="player_1")

    mock_print.assert_not_called()


def test_human_wolf_viewer_sees_live_wolf_discussion_without_late_panel(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(
            EventType.PLAYER_DISCUSSION,
            phase=GamePhase.NIGHT,
            data={"player_name": "玩家6", "speech": "我建议首刀1号。"},
            visible_to=["player_6", "player_7"],
        ),
        viewer_id="player_7",
    )
    presenter.present_event(
        _event(
            EventType.MESSAGE,
            message="🐺 狼人正在选择目标...",
            phase=GamePhase.NIGHT,
            data={"action": "werewolves_vote"},
            visible_to=["player_6", "player_7"],
        ),
        viewer_id="player_7",
    )

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    panels = [
        call.args[0]
        for call in mock_print.call_args_list
        if call.args and call.args[0].__class__.__name__ == "Panel"
    ]

    assert "🐺 玩家6: 我建议首刀1号。" in rendered
    assert "狼人正在选择目标" in rendered
    assert not panels


def test_present_game_lifecycle(presenter: ConsolePresenter, mock_print) -> None:
    presenter.present_event(_event(EventType.GAME_STARTED, data={"player_count": 6}))
    presenter.present_event(
        _event(
            EventType.GAME_ENDED,
            data={"winner_camp": "werewolf", "winner_ids": ["p1"]},
        )
    )
    assert mock_print.call_count >= 2


def test_present_phase_changes_flush_buffers(presenter: ConsolePresenter, mock_print) -> None:
    presenter.present_event(
        _event(
            EventType.PLAYER_SPEECH,
            data={"player_name": "A", "speech": "hello"},
        )
    )
    presenter.present_event(
        _event(
            EventType.PHASE_CHANGED,
            phase=GamePhase.NIGHT,
            data={"phase": "night", "round": 1},
        )
    )
    presenter.present_event(
        _event(
            EventType.PHASE_CHANGED,
            phase=GamePhase.DAY_DISCUSSION,
            data={"phase": "day_discussion", "round": 1},
        )
    )
    assert mock_print.call_count >= 3
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "第 1 轮 - 黑夜" in rendered
    assert "第 1 轮 - 白天" in rendered
    assert "第 1 輪 - 黑夜" not in rendered


def test_sheriff_election_phase_has_own_header(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(
            EventType.PHASE_CHANGED,
            phase=GamePhase.SHERIFF_ELECTION,
            data={"phase": "sheriff_election", "round": 1},
        )
    )

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "第 1 轮 - 警长竞选" in rendered


def test_present_narrator_messages(presenter: ConsolePresenter, mock_print) -> None:
    for action in (
        "night_falls",
        "werewolves_wake",
        "werewolves_vote",
        "werewolves_sleep",
        "daybreak",
        "unknown_action",
    ):
        presenter.present_event(
            _event(EventType.MESSAGE, data={"action": action}, message=f"msg-{action}")
        )
    assert mock_print.call_count >= len(
        ("night_falls", "werewolves_wake", "werewolves_vote", "werewolves_sleep", "daybreak", "unknown_action")
    )
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "请睁眼" in rendered
    assert "請睜眼" not in rendered


def test_present_night_actions_and_flush(presenter: ConsolePresenter, mock_print) -> None:
    for etype in (
        EventType.GUARD_PROTECTED,
        EventType.WITCH_SAVED,
        EventType.WITCH_POISON_USED,
        EventType.SEER_CHECKED,
        EventType.WEREWOLF_KILLED,
        EventType.LOVERS_LINKED,
    ):
        presenter.present_event(_event(etype, message="night action", phase=GamePhase.NIGHT))
    presenter.present_event(
        _event(EventType.PHASE_CHANGED, phase=GamePhase.DAY_DISCUSSION, data={"phase": "day", "round": 1})
    )
    assert mock_print.call_count >= 1


def test_present_player_and_vote_events(presenter: ConsolePresenter, mock_print) -> None:
    presenter.present_event(_event(EventType.PLAYER_DIED, data={"player_name": "A"}))
    presenter.present_event(
        _event(
            EventType.PLAYER_SPEECH,
            data={"player_name": "B", "speech": "speech"},
        )
    )
    presenter.present_event(
        _event(
            EventType.PLAYER_DISCUSSION,
            data={"player_name": "W", "speech": "wolf talk"},
            phase=GamePhase.NIGHT,
        )
    )
    presenter.present_event(_event(EventType.PLAYER_ELIMINATED, data={"player_name": "C"}))
    presenter.present_event(
        _event(EventType.VOTE_CAST, data={"voter_name": "D", "target_name": "E"})
    )
    presenter.present_event(_event(EventType.VOTE_RESULT, message="📊 vote stats"))
    assert mock_print.call_count >= 1


def test_human_viewer_sees_live_speech_without_discussion_buffer(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(
            EventType.PLAYER_SPEECH,
            data={"player_name": "玩家2", "speech": "我先听后置位发言。"},
        ),
        viewer_id="player_1",
    )
    presenter.present_event(_event(EventType.VOTE_RESULT, message="📊 stats"), viewer_id="player_1")

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "玩家2: 我先听后置位发言。" in rendered
    assert "玩家发言" not in rendered


def test_present_special_events(presenter: ConsolePresenter, mock_print) -> None:
    presenter.present_event(_event(EventType.HUNTER_REVENGE, data={"player_name": "H"}))
    presenter.present_event(_event(EventType.SHERIFF_ELECTED, data={"player_name": "S"}))
    presenter.present_event(_event(EventType.SHERIFF_VOTE_CAST, data={"voter_name": "V"}))
    presenter.present_event(_event(EventType.ROLE_REVEALED, data={"player_name": "R", "role": "Seer"}))
    assert mock_print.call_count >= 1


def test_present_vote_table_and_discussion_flush(presenter: ConsolePresenter, mock_print) -> None:
    presenter.present_event(
        _event(
            EventType.PLAYER_SPEECH,
            data={"player_name": "A", "speech": "line1"},
        )
    )
    presenter.present_event(
        _event(EventType.VOTE_CAST, data={"voter_name": "B", "target_name": "C"})
    )
    presenter.present_event(
        _event(EventType.VOTE_CAST, data={"voter_name": "D", "target_name": "C"})
    )
    presenter.present_event(_event(EventType.VOTE_RESULT, message="📊 stats"))
    assert mock_print.call_count >= 1
    tables = [
        call.args[0]
        for call in mock_print.call_args_list
        if call.args and call.args[0].__class__.__name__ == "Table"
    ]
    assert tables
    headers = [column.header for column in tables[-1].columns]
    assert headers == ["排名", "候选人", "票数", "投票者"]


def test_belief_snapshot_flushes_buffered_speech_first(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(
            EventType.PLAYER_SPEECH,
            data={"player_name": "玩家1", "speech": "我是预言家，昨晚验了4号是好人。"},
        )
    )
    presenter.present_event(
        _event(EventType.BELIEF_SNAPSHOT, message="【信念矩阵 · 听完 玩家1 发言后】")
    )

    calls = [call.args[0] for call in mock_print.call_args_list if call.args]
    speech_index = next(
        index for index, value in enumerate(calls) if "玩家1: 我是预言家" in str(value)
    )
    panel_index = next(
        index for index, value in enumerate(calls) if value.__class__.__name__ == "Panel"
    )
    assert speech_index < panel_index


def test_vote_intention_flushes_buffered_speech_first(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(
            EventType.PLAYER_SPEECH,
            data={"player_name": "玩家2", "speech": "我先支持警长安排，再听后置位发言。"},
        )
    )
    presenter.present_event(
        _event(EventType.VOTE_INTENTION_SNAPSHOT, message="【意向变化】玩家3→玩家2")
    )

    calls = [call.args[0] for call in mock_print.call_args_list if call.args]
    speech_index = next(
        index for index, value in enumerate(calls) if "玩家2: 我先支持警长" in str(value)
    )
    intention_index = next(
        index for index, value in enumerate(calls) if "【意向变化】" in str(value)
    )
    assert speech_index < intention_index


def test_human_viewer_vote_table_includes_public_votes(
    presenter: ConsolePresenter, mock_print
) -> None:
    presenter.present_event(
        _event(EventType.VOTE_CAST, data={"voter_name": "玩家1", "target_name": "玩家2"}),
        viewer_id="player_1",
    )
    presenter.present_event(
        _event(EventType.VOTE_CAST, data={"voter_name": "玩家3", "target_name": "玩家2"}),
        viewer_id="player_1",
    )
    presenter.present_event(
        _event(EventType.VOTE_CAST, data={"voter_name": "玩家4", "target_name": "玩家5"}),
        viewer_id="player_1",
    )
    presenter.present_event(_event(EventType.VOTE_RESULT, message="📊 stats"), viewer_id="player_1")

    tables = [
        call.args[0]
        for call in mock_print.call_args_list
        if call.args and call.args[0].__class__.__name__ == "Table"
    ]
    assert tables
    table = tables[-1]
    assert table.columns[1]._cells == ["玩家2", "玩家5"]
    assert table.columns[2]._cells == ["2", "1"]
    assert table.columns[3]._cells == ["玩家1, 玩家3", "玩家4"]


def test_present_game_start_includes_player_count(presenter: ConsolePresenter, mock_print) -> None:
    presenter.present_event(_event(EventType.GAME_STARTED, data={"player_count": 6}))
    assert mock_print.call_count >= 1
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "游戏开始" in rendered
    assert "玩家人数" in rendered
    assert "遊戲開始" not in rendered


def test_present_default_style_for_unknown_event(presenter: ConsolePresenter, mock_print) -> None:
    presenter.present_event(_event(EventType.MESSAGE, message="plain"))
    mock_print.assert_called()
