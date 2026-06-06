import json
from pathlib import Path

from fastapi.testclient import TestClient

from llm_werewolf.interface.api.app import create_app


def _write_events(run_dir: Path, events: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    (run_dir / "run_meta.json").write_text(
        json.dumps({"run_id": run_dir.name, "status": "completed"}), encoding="utf-8"
    )


def test_stream_replays_completed_run_god_view(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "demo-stream"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    _write_events(
        run_dir,
        [
            {"event_type": "game_started", "round_number": 0, "phase": "setup",
             "message": "start", "data": {}, "visible_to": None},
            {"event_type": "seer_checked", "round_number": 1, "phase": "night",
             "message": "查验", "data": {}, "visible_to": ["player_2"]},
            {"event_type": "vote_result", "round_number": 1, "phase": "day_voting",
             "message": "出局", "data": {}, "visible_to": None},
        ],
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=god") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = "".join(chunk for chunk in resp.iter_text())
    # god view: all three event types appear
    assert "game_started" in body
    assert "seer_checked" in body
    assert "vote_result" in body


def test_stream_seat_view_hides_other_players_private_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "demo-stream2"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    _write_events(
        run_dir,
        [
            {"event_type": "seer_checked", "round_number": 1, "phase": "night",
             "message": "查验", "data": {}, "visible_to": ["player_2"]},
            {"event_type": "vote_result", "round_number": 1, "phase": "day_voting",
             "message": "出局", "data": {}, "visible_to": None},
        ],
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=seat&seat=3") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    assert "vote_result" in body        # public -> visible
    assert "seer_checked" not in body   # seat 3 must NOT see seat 2's private event


def test_stream_unknown_run_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())
    resp = client.get("/api/v1/games/nope/stream?view=god")
    assert resp.status_code == 404
