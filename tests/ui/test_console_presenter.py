from llm_werewolf.game_runtime.types import Event, EventType, GamePhase
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.ui import console_presenter as presenter_module
from llm_werewolf.ui.console_presenter import ConsolePresenter


def test_human_viewer_sees_own_private_night_event(monkeypatch) -> None:
    printed: list[str] = []
    monkeypatch.setattr(
        presenter_module.console,
        "print",
        lambda *args, **_kwargs: printed.append(" ".join(str(arg) for arg in args)),
    )
    presenter = ConsolePresenter(Locale("zh-CN"))
    event = Event(
        event_type=EventType.SEER_CHECKED,
        round_number=1,
        phase=GamePhase.NIGHT,
        message="预言家查验了 2 号，结果为好人。",
        data={"player_id": "player_1"},
        visible_to=["player_1"],
    )

    presenter.present_event(event, viewer_id="player_1")

    assert any("预言家查验" in line for line in printed)


def test_human_viewer_does_not_see_other_private_event(monkeypatch) -> None:
    printed: list[str] = []
    monkeypatch.setattr(
        presenter_module.console,
        "print",
        lambda *args, **_kwargs: printed.append(" ".join(str(arg) for arg in args)),
    )
    presenter = ConsolePresenter(Locale("zh-CN"))
    event = Event(
        event_type=EventType.SEER_CHECKED,
        round_number=1,
        phase=GamePhase.NIGHT,
        message="预言家查验了 2 号，结果为好人。",
        data={"player_id": "player_2"},
        visible_to=["player_2"],
    )

    presenter.present_event(event, viewer_id="player_1")

    assert printed == []
