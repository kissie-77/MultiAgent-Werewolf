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


def test_stream_web_human_seat_requires_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "web-human-stream"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    _write_events(run_dir, [])
    meta = {
        "run_id": run_id,
        "status": "running",
        "web_human_seat": 2,
        "player_token": f"seat2-{run_id}",
    }
    (run_dir / "run_meta.json").write_text(json.dumps(meta), encoding="utf-8")

    client = TestClient(create_app())
    no_token = client.get(f"/api/v1/games/{run_id}/stream?view=seat&seat=2")
    assert no_token.status_code == 403

    bad_token = client.get(
        f"/api/v1/games/{run_id}/stream?view=seat&seat=2&token=wrong"
    )
    assert bad_token.status_code == 403

    wrong_seat = client.get(
        f"/api/v1/games/{run_id}/stream?view=seat&seat=3&token=seat2-{run_id}"
    )
    assert wrong_seat.status_code == 403

    ok = client.get(
        f"/api/v1/games/{run_id}/stream?view=seat&seat=2&token=seat2-{run_id}"
    )
    assert ok.status_code == 200


def test_stream_unknown_run_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())
    resp = client.get("/api/v1/games/nope/stream?view=god")
    assert resp.status_code == 404


def test_god_snapshot_builds_roster_from_events_when_god_roster_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "6p-demo-events"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    _write_events(
        run_dir,
        [
            {
                "event_type": "role_acting",
                "round_number": 1,
                "phase": "night",
                "data": {"player_id": "player_1", "player_name": "A", "role": "Seer"},
            },
            {
                "event_type": "role_acting",
                "round_number": 1,
                "phase": "night",
                "data": {"player_id": "player_2", "player_name": "B", "role": "Werewolf"},
            },
        ],
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=god") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    assert '"roster"' in body
    assert "Seer" in body


def test_god_snapshot_includes_roster_when_present(tmp_path, monkeypatch):
    import json
    from fastapi.testclient import TestClient
    from llm_werewolf.interface.api.app import create_app

    monkeypatch.chdir(tmp_path)
    run_id = "demo-roster"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "run_meta.json").write_text(json.dumps({"run_id": run_id, "status": "completed"}), encoding="utf-8")
    (run_dir / "god_roster.json").write_text(
        json.dumps([{"seat": 1, "name": "Player1", "role": "Seer", "camp": "villager", "is_alive": True}]),
        encoding="utf-8",
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=god") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    assert '"roster"' in body
    assert "Seer" in body

    # seat view must NOT leak the roster
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=seat&seat=1") as resp:
        body2 = "".join(chunk for chunk in resp.iter_text())
    assert "Seer" not in body2


async def test_engine_run_publishes_to_broadcaster(tmp_path, monkeypatch):
    """A real (demo) game wired through GameSessionManager's composite on_event
    both writes events.jsonl and fans out to a live subscriber."""
    monkeypatch.chdir(tmp_path)
    import asyncio
    from llm_werewolf.interface.api.services import event_stream
    from llm_werewolf.interface.api.services.game_sessions import game_session_manager
    from llm_werewolf.interface.api.models.actions import StartGameRequest
    from llm_werewolf.interface.api.deps import get_runs_dir, get_configs_dir

    # demo config ships in repo configs/; copy is unnecessary — resolve_config_for_start
    # accepts a config_id under the repo configs dir.
    from tests.interface.fixtures import write_standard_demo_config

    configs_dir = tmp_path / "configs"
    write_standard_demo_config(configs_dir, player_count=6)
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    resp = await game_session_manager.start_game(
        configs_dir=configs_dir, runs_dir=runs_dir,
        request=StartGameRequest(config_id="standard-6p"),
    )
    run_id = resp.run_id
    # The _run_game task is scheduled but has not yet run (start_game never
    # yields to the loop), so the broadcaster may not be registered yet.
    # get_or_create returns the same idempotent instance _run_game will reuse,
    # letting us subscribe before the game produces events.
    b = event_stream.get_or_create_broadcaster(run_id)
    assert b is not None

    received: list[dict] = []

    async def consume() -> None:
        async for ev in b.subscribe():
            received.append(ev)

    consumer = asyncio.create_task(consume())
    # wait for the game task to finish (demo agents are fast/offline)
    session = game_session_manager._sessions[run_id]
    await asyncio.wait_for(session.task, timeout=120)
    await asyncio.sleep(0.05)
    consumer.cancel()

    assert (runs_dir / run_id / "events.jsonl").is_file()
    types = {e["event_type"] for e in received}
    assert "game_started" in types or len(received) > 0
