"""Task 6: wire the web-human seat + token + input broker into the game session.

Two complementary tests:

1. ``test_start_game_overrides_human_seat_to_web_human`` — deterministic unit check that
   ``start_game`` overrides the requested seat's ``PlayerConfig`` to the ``web-human``
   builtin model (clearing any LLM key/base_url), mints a seat token, and fills the
   response ``player_token`` / ``stream_path``.

2. ``test_web_human_game_pauses_and_resumes`` — full demo-6 game where seat 1 is the
   web-human. The seat's agent blocks on the broker at every decision; a driver task
   submits ``"0"`` to advance it, proving the pause/resume loop does not deadlock. The
   broker wiring itself is asserted deterministically: the captured seat-1 agent is a
   ``WebHumanAgent`` whose ``broker`` is the session's ``input_broker``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import llm_werewolf.interface.api.services.game_sessions as gs_mod
from llm_werewolf.interface.api.services.game_sessions import (
    GameSessionStatus,
    GameSessionManager,
)
from llm_werewolf.interface.api.services.human_input import get_input_broker
from llm_werewolf.interface.api.models.actions import StartGameRequest

_CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs"


async def test_start_game_overrides_human_seat_to_web_human(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    mgr = GameSessionManager()
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    req = StartGameRequest(config_id="demo-6", human={"seat": 1})
    resp = await mgr.start_game(configs_dir=_CONFIGS_DIR, runs_dir=runs_dir, request=req)

    # Response carries the seat token + stream path for the browser seat-view subscription.
    assert resp.player_token == f"seat1-{resp.run_id}"
    assert resp.stream_path == f"/api/v1/games/{resp.run_id}/stream"

    session = mgr._sessions[resp.run_id]
    assert session.human_seat == 1
    assert session.player_token == resp.player_token

    # Seat 1 is now the web-human builtin model with no LLM credentials.
    seat1 = session.players_config.players[0]
    assert seat1.model == "web-human"
    assert seat1.api_key_env is None
    assert seat1.base_url is None
    # Other seats are untouched.
    assert session.players_config.players[1].model == "demo"

    # The background task would block on the (driver-less) broker; cancel it for cleanup.
    await mgr.cancel_game(resp.run_id)


async def test_web_human_game_pauses_and_resumes(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    mgr = GameSessionManager()
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Capture the built roster so we can assert the seat-1 agent got the broker wired in.
    captured: dict[str, object] = {}
    real_prepare = gs_mod.prepare_game_roster

    def _capture(players_config):
        players, roles, cfg = real_prepare(players_config)
        captured["players"] = players
        return players, roles, cfg

    monkeypatch.setattr(gs_mod, "prepare_game_roster", _capture)

    req = StartGameRequest(config_id="demo-6", human={"seat": 1})
    resp = await mgr.start_game(configs_dir=_CONFIGS_DIR, runs_dir=runs_dir, request=req)
    assert resp.player_token and resp.stream_path

    session = mgr._sessions[resp.run_id]
    submitted = 0

    async def _drive() -> None:
        nonlocal submitted
        while True:
            broker = get_input_broker(resp.run_id)
            if broker is not None:
                for rid in list(broker.pending_ids()):
                    if broker.submit(request_id=rid, payload="0"):
                        submitted += 1
            await asyncio.sleep(0.01)

    driver = asyncio.create_task(_drive())
    try:
        await asyncio.wait_for(session.task, timeout=60)
    finally:
        driver.cancel()

    # The game advanced to a terminal state instead of hanging on the human seat.
    assert session.status in {GameSessionStatus.COMPLETED, GameSessionStatus.FAILED}

    # Broker was wired into the session and into the seat-1 agent (deterministic proof).
    assert session.input_broker is not None
    seat1_agent = captured["players"][0]
    assert type(seat1_agent).__name__ == "WebHumanAgent"
    assert seat1_agent.seat == 1
    assert seat1_agent.broker is session.input_broker

    # Broker is unregistered on teardown.
    assert get_input_broker(resp.run_id) is None
