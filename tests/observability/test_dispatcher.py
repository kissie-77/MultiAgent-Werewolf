"""Tests for observability dispatcher and rules."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_werewolf.evaluation.core.models import CheckResult, CheckSeverity
from llm_werewolf.observability.core.config import ObservabilityConfig
from llm_werewolf.observability.core.dispatcher import AlertDispatcher
from llm_werewolf.observability.core.models import AlertEvent, AlertSeverity
from llm_werewolf.observability.rules.engine import evaluate_run_signals


@pytest.mark.asyncio
async def test_dispatcher_dedupes_same_code(tmp_path: Path) -> None:
    config = ObservabilityConfig.from_env(alerts_dir=tmp_path / "alerts")
    config.dedupe_ttl_seconds = 300
    dispatcher = AlertDispatcher(config, notifiers=[])
    event = AlertEvent(
        run_id="run-1",
        source="test",
        severity=AlertSeverity.WARNING,
        code="error_events_per_run",
        message="too many errors",
    )
    first = await dispatcher.emit([event], run_dir=tmp_path / "run-1")
    second = await dispatcher.emit([event], run_dir=tmp_path / "run-1")
    assert len(first) == 1
    assert second == []


def test_dispatcher_prunes_expired_dedupe_keys(tmp_path: Path) -> None:
    config = ObservabilityConfig.from_env(alerts_dir=tmp_path / "alerts")
    config.dedupe_ttl_seconds = 60
    dispatcher = AlertDispatcher(config, notifiers=[])
    event_a = AlertEvent(
        run_id="run-1",
        source="test",
        severity=AlertSeverity.WARNING,
        code="error_events_per_run",
        message="too many errors",
    )
    event_b = AlertEvent(
        run_id="run-1",
        source="test",
        severity=AlertSeverity.WARNING,
        code="checker_critical",
        message="leak",
    )
    with patch("llm_werewolf.observability.core.dispatcher.time.time", return_value=1000.0):
        assert dispatcher._should_emit(event_a) is True
        assert dispatcher._should_emit(event_b) is True
        assert len(dispatcher._recent) == 2

    with patch("llm_werewolf.observability.core.dispatcher.time.time", return_value=1070.0):
        assert dispatcher._should_emit(event_a) is True
        assert event_a.dedupe_key() in dispatcher._recent
        assert event_b.dedupe_key() not in dispatcher._recent
        assert len(dispatcher._recent) == 1
        assert dispatcher._should_emit(event_b) is True
        assert len(dispatcher._recent) == 2


def test_evaluate_run_failed_signal() -> None:
    config = ObservabilityConfig.from_env()
    signals = {
        "run_id": "demo-run",
        "run_meta": {"status": "failed", "error": "boom"},
        "post_game": {},
        "checks": [],
    }
    alerts = evaluate_run_signals(signals, config)
    assert any(alert.code == "run_failed" for alert in alerts)


def test_evaluate_checker_critical_via_collector(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-critical"
    run_dir.mkdir()
    (run_dir / "run_meta.json").write_text(
        json.dumps({"run_id": "run-critical", "status": "completed"}),
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "game_started",
                "timestamp": "2026-06-02T12:00:00",
                "round_number": 0,
                "phase": "setup",
                "message": "start",
                "data": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    from llm_werewolf.observability.collectors.run_artifact_collector import RunArtifactCollector

    collector = RunArtifactCollector(ObservabilityConfig.from_env())
    # Inject a critical failure without running full checker suite
    signals = {
        "run_id": "run-critical",
        "checks": [
            CheckResult(
                checker="InformationIsolationChecker",
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message="leak detected",
            )
        ],
    }
    from llm_werewolf.observability.collectors.checker_collector import collect_checker_alerts

    alerts = collect_checker_alerts(signals, ObservabilityConfig.from_env())
    assert alerts and alerts[0].code == "checker_critical"

    # Full collector path should not crash on minimal run dir
    collector.collect(run_dir)
