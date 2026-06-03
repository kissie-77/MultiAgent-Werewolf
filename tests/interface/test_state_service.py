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
