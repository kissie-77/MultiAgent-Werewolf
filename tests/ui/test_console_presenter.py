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
    event = _event(EventType.SEER_CHECKED, phase=GamePhase.NIGHT)
    presenter.present_event(event, viewer_id="player_1")
    mock_print.assert_not_called()


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
            data={"phase": "day", "round": 1},
        )
    )
    assert mock_print.call_count >= 3
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "第 1 轮 - 黑夜" in rendered
    assert "第 1 輪 - 黑夜" not in rendered


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
        EventType.WITCH_POISONED,
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
