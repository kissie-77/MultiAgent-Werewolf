from types import SimpleNamespace

import pytest

from llm_werewolf.game_runtime.engine.day_phase import DayPhaseMixin
from llm_werewolf.game_runtime.engine.voting_phase import VotingPhaseMixin
from llm_werewolf.game_runtime.locale import Locale


class _FailingRoundtableInteraction:
    async def run_roundtable(self, *args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        raise TimeoutError()


class _FailingVoteInteraction:
    async def request_seat_choice(self, *args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        raise TimeoutError()


class _DummyPlayer:
    def __init__(self, name: str, player_id: str) -> None:
        self.name = name
        self.player_id = player_id
        self.agent = SimpleNamespace(add_decision=lambda *_args, **_kwargs: None)

    def can_vote(self) -> bool:
        return True

    def get_role_name(self) -> str:
        return "Villager"


class _DummyDayEngine(DayPhaseMixin):
    def __init__(self) -> None:
        self.locale = Locale("zh-CN")
        self.events: list[tuple[str, str, dict]] = []
        self.game_state = SimpleNamespace(
            round_number=1,
            night_deaths=[],
            belief_log=None,
            vote_intention_tracker=None,
            track_vote_intentions=False,
            set_phase=lambda _phase: None,
            get_alive_players=lambda: [],
            require_phase_interaction=lambda: _FailingRoundtableInteraction(),
        )

    def _log_event(self, event_type, message, data=None, visible_to=None) -> None:  # noqa: ANN001
        del visible_to
        self.events.append((event_type, message, data or {}))

    def build_player_observation(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        del args, kwargs
        return ""


class _DummyVotingEngine(VotingPhaseMixin):
    def __init__(self) -> None:
        self.locale = Locale("zh-CN")
        self.events: list[tuple[str, str, dict]] = []
        player = _DummyPlayer(name="玩家1", player_id="player_1")
        self.game_state = SimpleNamespace(
            round_number=1,
            votes={},
            get_alive_players=lambda except_ids=None: [  # noqa: B023
                p for p in [player, _DummyPlayer(name="玩家2", player_id="player_2")] if p.player_id not in (except_ids or [])
            ],
            require_phase_interaction=lambda: _FailingVoteInteraction(),
        )

    def _log_event(self, event_type, message, data=None, visible_to=None) -> None:  # noqa: ANN001
        del visible_to
        self.events.append((event_type, message, data or {}))

    def build_player_observation(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        del args, kwargs
        return ""


@pytest.mark.asyncio
async def test_day_phase_logs_non_empty_error_for_blank_exception_message() -> None:
    engine = _DummyDayEngine()

    await engine.run_day_phase()

    error_events = [event for event in engine.events if event[0] == "error"]
    assert error_events
    _, message, data = error_events[-1]
    assert "TimeoutError" in message
    assert data["error"] == "TimeoutError"


@pytest.mark.asyncio
async def test_voting_phase_logs_non_empty_error_for_blank_exception_message() -> None:
    engine = _DummyVotingEngine()

    await engine._collect_votes()

    error_events = [event for event in engine.events if event[0] == "error"]
    assert error_events
    _, message, data = error_events[-1]
    assert "TimeoutError" in message
    assert data["error"] == "TimeoutError"
