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


def test_redact_event_for_seat_strips_private_fields() -> None:
    from llm_werewolf.interface.api.services.event_stream import redact_event_for_seat

    ev = {
        "event_type": "player_speech",
        "data": {
            "player_id": "player_2",
            "role": "Werewolf",
            "reasoning": "secret plan",
            "private_thought": "inner monologue",
            "content": "hello",
        },
    }
    out = redact_event_for_seat(ev, seat=1)
    assert out["data"]["content"] == "hello"
    assert "reasoning" not in out["data"]
    assert "private_thought" not in out["data"]
    assert "role" not in out["data"]

    self_ev = redact_event_for_seat(
        {
            "event_type": "actor_thinking",
            "data": {"player_id": "player_1", "role": "Seer"},
        },
        seat=1,
    )
    assert self_ev["data"]["role"] == "Seer"

    other_ev = redact_event_for_seat(
        {
            "event_type": "actor_thinking",
            "data": {"player_id": "player_2", "role": "Werewolf"},
        },
        seat=1,
    )
    assert "role" not in other_ev["data"]


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


def test_stream_seat_view_redacts_speech_roles_in_replay(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "demo-redact-speech"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    _write_events(
        run_dir,
        [
            {
                "event_type": "player_speech",
                "round_number": 1,
                "phase": "day_discussion",
                "message": "hello",
                "data": {
                    "player_id": "player_2",
                    "role": "Werewolf",
                    "reasoning": "secret",
                    "private_thought": "inner",
                    "content": "hello",
                },
                "visible_to": None,
            },
        ],
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=seat&seat=1") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    assert "player_speech" in body
    assert "hello" in body
    assert '"role": "Werewolf"' not in body
    assert '"reasoning": "secret"' not in body
    assert '"private_thought": "inner"' not in body


def test_stream_unknown_run_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())
    resp = client.get("/api/v1/games/nope/stream?view=god")
    assert resp.status_code == 404


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
        json.dumps([
            {"seat": 1, "name": "Player1", "role": "Seer", "camp": "villager", "is_alive": True},
            {"seat": 2, "name": "Player2", "role": "Werewolf", "camp": "werewolf", "is_alive": True},
        ]),
        encoding="utf-8",
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=god") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    assert '"roster"' in body
    assert "Seer" in body and "Werewolf" in body  # god sees every role

    # seat view sends a REDACTED roster: own role revealed, others hidden
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=seat&seat=1") as resp:
        body2 = "".join(chunk for chunk in resp.iter_text())
    assert '"roster"' in body2          # roster present (so cards render)
    assert "Seer" in body2              # the requesting seat's own role
    assert "Werewolf" not in body2      # another seat's role must NOT leak


async def test_engine_run_publishes_to_broadcaster(tmp_path, monkeypatch):
    """A real (demo) game wired through GameSessionManager's composite on_event
    both writes events.jsonl and fans out to a live subscriber.
    """
    monkeypatch.chdir(tmp_path)
    import asyncio

    from llm_werewolf.interface.api.services import event_stream
    from llm_werewolf.interface.api.models.actions import StartGameRequest
    from llm_werewolf.interface.api.services.game_sessions import game_session_manager

    # demo config ships in repo configs/; copy is unnecessary — resolve_config_for_start
    # accepts a config_id under the repo configs dir.
    configs_dir = Path(__file__).resolve().parents[2] / "configs"
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    resp = await game_session_manager.start_game(
        configs_dir=configs_dir, runs_dir=runs_dir,
        request=StartGameRequest(config_id="demo-6"),
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
