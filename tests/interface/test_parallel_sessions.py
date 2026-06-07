"""Concurrent game opens get isolated run_ids, dirs, and event logs."""

from __future__ import annotations

import asyncio
from pathlib import Path

from llm_werewolf.interface.api.services.game_sessions import (
    GameSessionStatus,
    GameSessionManager,
)
from llm_werewolf.interface.api.models.actions import StartGameRequest

_CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs"


async def test_two_concurrent_demo_games_are_isolated(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    mgr = GameSessionManager()
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    req = StartGameRequest(config_id="demo-6")
    r1, r2 = await asyncio.gather(
        mgr.start_game(configs_dir=_CONFIGS_DIR, runs_dir=runs_dir, request=req),
        mgr.start_game(configs_dir=_CONFIGS_DIR, runs_dir=runs_dir, request=req),
    )
    try:
        # Distinct run ids and distinct directories.
        assert r1.run_id != r2.run_id
        assert (runs_dir / r1.run_id).is_dir()
        assert (runs_dir / r2.run_id).is_dir()
        # Both sessions live in the registry simultaneously.
        assert r1.run_id in mgr._sessions
        assert r2.run_id in mgr._sessions
        # Let both play to completion (demo games are fast, no LLM key needed).
        await asyncio.wait_for(
            asyncio.gather(
                mgr._sessions[r1.run_id].task,
                mgr._sessions[r2.run_id].task,
            ),
            timeout=120,
        )
        # Each wrote its own events.jsonl independently.
        e1 = runs_dir / r1.run_id / "events.jsonl"
        e2 = runs_dir / r2.run_id / "events.jsonl"
        assert e1.is_file() and e2.is_file()
        assert mgr._sessions[r1.run_id].status == GameSessionStatus.COMPLETED
        assert mgr._sessions[r2.run_id].status == GameSessionStatus.COMPLETED
    finally:
        for rid in (r1.run_id, r2.run_id):
            sess = mgr._sessions.get(rid)
            if sess and sess.task and not sess.task.done():
                await mgr.cancel_game(rid)
