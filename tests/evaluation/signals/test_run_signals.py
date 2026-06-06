"""Tests for evaluation signals."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from llm_werewolf.evaluation.signals.post_game_signals import (
    derive_post_game_status,
    load_post_game_signals,
)
from llm_werewolf.evaluation.signals.run_scan import scan_run_dir


def test_load_post_game_signals_detects_failed_step(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    payload = {
        "schema": "post_game_steps_v1",
        "steps": [
            {"step_id": "load_context", "status": "ok", "duration_ms": 1.0},
            {"step_id": "llm_replay", "status": "failed", "duration_ms": 2.0, "error": "boom"},
        ],
        "summary": {"total": 2, "ok": 1, "failed": 1, "skipped": 0},
    }
    (run_dir / "post_game_steps.json").write_text(json.dumps(payload), encoding="utf-8")
    signals = load_post_game_signals(run_dir)
    assert signals["post_game_status"] == "failed"
    assert "llm_replay" in signals["failed_steps"]


def test_scan_run_dir_counts_runtime_errors(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    lines = []
    for idx in range(4):
        lines.append(
            json.dumps(
                {
                    "event_type": "error",
                    "timestamp": "2026-06-02T12:00:00",
                    "round_number": 1,
                    "phase": "day_voting",
                    "message": "vote failed",
                    "data": {"error": "timeout", "error_type": "TimeoutError"},
                }
            )
        )
    (run_dir / "events.jsonl").write_text("\n".join(lines), encoding="utf-8")
    checks = scan_run_dir(run_dir, include_heavy_checkers=False)
    runtime_errors = [c for c in checks if c.checker == "RuntimeErrorEventChecker"]
    assert len(runtime_errors) == 4


def test_derive_post_game_status() -> None:
    assert derive_post_game_status(result_ok=True, error=None) == "ok"
    assert derive_post_game_status(result_ok=False, error="failed") == "failed"
    assert derive_post_game_status(result_ok=True, error=None, stage_errors={"llm": "x"}) == "failed"


def test_runtime_log_handler_records_429(tmp_path: Path) -> None:
    from llm_werewolf.observability.core.runtime_log import (
        attach_run_log_handler,
        count_provider_events,
        detach_run_log_handler,
        load_provider_events,
    )

    run_dir = tmp_path / "run"
    attach_run_log_handler(run_dir)
    try:
        logging.getLogger("llm_werewolf.agent_team.test").warning("provider returned 429 Too Many Requests")
    finally:
        detach_run_log_handler()

    events = load_provider_events(run_dir)
    assert count_provider_events(events, "provider_429") == 1


def test_runtime_log_handler_records_fallback(tmp_path: Path) -> None:
    from llm_werewolf.observability.core.runtime_log import (
        attach_run_log_handler,
        count_provider_events,
        detach_run_log_handler,
        load_provider_events,
    )

    run_dir = tmp_path / "run"
    attach_run_log_handler(run_dir)
    try:
        logging.getLogger("llm_werewolf.agent_team.bridge").warning(
            "request_speech failed agent=Player1, using fallback"
        )
    finally:
        detach_run_log_handler()

    events = load_provider_events(run_dir)
    assert count_provider_events(events, "agent_fallback") == 1
