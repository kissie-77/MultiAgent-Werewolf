"""Unit tests for the /state composition service and engine wiring."""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.interface.api.services.game_sessions import GameSession


def _make_session(tmp_path: Path) -> GameSession:
    return GameSession(
        run_id="r1",
        run_dir=tmp_path,
        config_path=tmp_path / "cfg.yaml",
        config_id="demo-6",
    )


def test_game_session_has_engine_field_defaulting_none(tmp_path):
    session = _make_session(tmp_path)
    assert session.engine is None


from llm_werewolf.interface.api.models.state import (
    GameStateResponse,
    LastNight,
    StatePlayer,
    StateVotes,
)


def test_state_models_defaults_match_spec():
    resp = GameStateResponse(status="running", phase="night", round=2)
    assert resp.play_state == "playing"
    assert resp.speed == 1
    assert resp.sub_phase is None
    assert resp.current_actor_seat is None
    assert resp.winner is None
    assert resp.error is None
    assert resp.last_night == LastNight()
    assert resp.votes == StateVotes()
    assert resp.players == []
    assert resp.cursor == 0


def test_state_player_status_flags_default_empty():
    p = StatePlayer(seat=1, name="P1")
    assert p.status_flags == []
    assert p.is_alive is True
    assert p.is_sheriff is False
