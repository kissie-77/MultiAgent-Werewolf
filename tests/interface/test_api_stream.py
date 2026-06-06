"""Integration tests for GET /games/{run_id}/stream (SSE)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from llm_werewolf.interface.api import deps
from llm_werewolf.interface.api.app import create_app


def _write_run(run_dir):
    run_dir.mkdir(parents=True)
    rows = [
        {"event_type": "game_started", "round_number": 0, "phase": "setup",
         "message": "", "data": {}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P1", "data": {"player_id": "player_1", "player_name": "P1", "speech": "a"}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P2", "data": {"player_id": "player_2", "player_name": "P2", "speech": "b"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )


def _client(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir / "done-1")
    app = create_app()
    app.dependency_overrides[deps.get_runs_dir] = lambda: runs_dir
    app.dependency_overrides[deps.get_eval_runs_dir] = lambda: runs_dir
    return TestClient(app)


def test_stream_finished_run_backfills_from_disk(tmp_path) -> None:
    # 3 disk rows => 0-based seqs 0, 1, 2 (matching build_view's _map_event idx).
    client = _client(tmp_path)
    with client.stream("GET", "/api/v1/games/done-1/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["cache-control"] == "no-cache"
        assert resp.headers["x-accel-buffering"] == "no"
        body = "".join(resp.iter_text())
    assert "id: 0\n" in body
    assert "id: 1\n" in body
    assert "id: 2\n" in body
    assert "event: game\n" in body


def test_stream_last_event_id_skips_seen(tmp_path) -> None:
    # Last-Event-ID=1 => client saw seq 0,1; only seq 2 is backfilled.
    client = _client(tmp_path)
    with client.stream(
        "GET", "/api/v1/games/done-1/stream", headers={"Last-Event-ID": "1"}
    ) as resp:
        body = "".join(resp.iter_text())
    assert "id: 0\n" not in body
    assert "id: 1\n" not in body
    assert "id: 2\n" in body


def test_stream_unknown_run_is_404(tmp_path) -> None:
    client = _client(tmp_path)
    resp = client.get("/api/v1/games/no-such-run/stream")
    assert resp.status_code == 404


import threading
import time

from llm_werewolf.interface.api.services.game_sessions import (
    GameSession,
    game_session_manager,
)


def _live_speech_row(pid: int) -> dict:
    return {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
            "message": f"P{pid}", "data": {"player_id": f"player_{pid}",
            "player_name": f"P{pid}", "speech": "x"}}


def test_stream_live_session_pushes_then_closes(tmp_path) -> None:
    game_session_manager.reset()
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "live-1"
    run_dir.mkdir(parents=True)
    session = GameSession(
        run_id="live-1", run_dir=run_dir,
        config_path=run_dir, config_id="c",
    )
    game_session_manager._sessions["live-1"] = session

    app = create_app()
    app.dependency_overrides[deps.get_runs_dir] = lambda: runs_dir
    app.dependency_overrides[deps.get_eval_runs_dir] = lambda: runs_dir
    client = TestClient(app)

    def _producer() -> None:
        time.sleep(0.2)
        session.hub.publish(_live_speech_row(1))  # seq 0
        session.hub.publish(_live_speech_row(2))  # seq 1
        time.sleep(0.1)
        session.hub.close()

    t = threading.Thread(target=_producer)
    t.start()
    with client.stream("GET", "/api/v1/games/live-1/stream") as resp:
        body = "".join(resp.iter_text())
    t.join()
    game_session_manager.reset()

    assert "id: 0\n" in body
    assert "id: 1\n" in body
    assert '"type": "speech"' in body
