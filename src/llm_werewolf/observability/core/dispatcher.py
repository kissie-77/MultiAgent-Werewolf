"""告警去重、节流、持久化与通知分发。"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any
import logging
from pathlib import Path

from llm_werewolf.observability.core.config import ObservabilityConfig, load_config
from llm_werewolf.observability.core.models import AlertEvent, AlertSeverity
from llm_werewolf.observability.notifiers.webhook import WebhookNotifier
from llm_werewolf.observability.collectors.run_artifact_collector import RunArtifactCollector

if TYPE_CHECKING:
    from llm_werewolf.observability.notifiers.base import AlertNotifier
    from llm_werewolf.evaluation.post_game.pipeline import PostGameResult

logger = logging.getLogger(__name__)


class AlertDispatcher:
    def __init__(
        self,
        config: ObservabilityConfig | None = None,
        *,
        notifiers: list[AlertNotifier] | None = None,
    ) -> None:
        self._config = config or load_config()
        self._collector = RunArtifactCollector(self._config)
        self._notifiers = notifiers if notifiers is not None else self._default_notifiers()
        self._recent: dict[str, float] = {}

    def _default_notifiers(self) -> list[AlertNotifier]:
        if not self._config.webhook_url:
            return []
        return [WebhookNotifier(self._config.webhook_url)]

    def _prune_recent(self, now: float) -> None:
        ttl = self._config.dedupe_ttl_seconds
        expired = [key for key, ts in self._recent.items() if now - ts >= ttl]
        for key in expired:
            del self._recent[key]

    def _should_emit(self, event: AlertEvent) -> bool:
        if not event.severity.meets_minimum(self._config.min_severity):
            return False
        key = event.dedupe_key()
        now = time.time()
        self._prune_recent(now)
        last = self._recent.get(key)
        if last is not None and now - last < self._config.dedupe_ttl_seconds:
            return False
        self._recent[key] = now
        return True

    def _append_audit(self, events: list[AlertEvent]) -> Path | None:
        if not events:
            return None
        alerts_dir = self._config.alerts_dir
        alerts_dir.mkdir(parents=True, exist_ok=True)
        audit_path = alerts_dir / "alerts.jsonl"
        with audit_path.open("a", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
        return audit_path

    def _write_run_report(self, run_dir: Path, events: list[AlertEvent]) -> None:
        if not events:
            return
        report = {
            "schema": "run_alert_report_v1",
            "run_id": events[0].run_id,
            "alert_count": len(events),
            "alerts": [event.model_dump(mode="json") for event in events],
        }
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "alert_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def emit(self, events: list[AlertEvent], *, run_dir: Path | None = None) -> list[AlertEvent]:
        accepted = [event for event in events if self._should_emit(event)]
        if not accepted:
            return []
        self._append_audit(accepted)
        if run_dir is not None:
            self._write_run_report(run_dir, accepted)
        for notifier in self._notifiers:
            try:
                await notifier.notify(accepted)
            except Exception as exc:
                logger.warning("Notifier failed: %s", exc)
        return accepted

    async def emit_from_run_dir(self, run_dir: Path) -> list[AlertEvent]:
        run_dir = Path(run_dir)
        events = self._collector.collect(run_dir)
        return await self.emit(events, run_dir=run_dir)

    async def emit_from_post_game(
        self,
        run_dir: Path,
        result: PostGameResult,
    ) -> list[AlertEvent]:
        run_dir = Path(run_dir)
        events = self._collector.collect(run_dir)
        if result.error and not any(event.code == "post_game_failed" for event in events):
            events.append(
                AlertEvent(
                    run_id=run_dir.name,
                    source="post_game",
                    severity=AlertSeverity.ERROR,
                    code="post_game_failed",
                    message=result.error,
                    context={"stage_errors": result.stage_errors},
                )
            )
        return await self.emit(events, run_dir=run_dir)

    async def emit_session_failed(
        self,
        *,
        run_id: str,
        run_dir: Path,
        error: str,
    ) -> list[AlertEvent]:
        event = AlertEvent(
            run_id=run_id,
            source="session",
            severity=AlertSeverity.ERROR,
            code="run_failed",
            message=error,
            context={"status": "failed"},
        )
        return await self.emit([event], run_dir=run_dir)


_default_dispatcher: AlertDispatcher | None = None


def get_dispatcher(config: ObservabilityConfig | None = None) -> AlertDispatcher:
    global _default_dispatcher
    if config is not None:
        return AlertDispatcher(config)
    if _default_dispatcher is None:
        _default_dispatcher = AlertDispatcher()
    return _default_dispatcher


def update_run_meta_alerts(run_dir: Path, *, post_game_status: str, alert_count: int) -> None:
    """扩展 run_meta.json：post_game_status 与 alert_count。"""
    run_dir = Path(run_dir)
    meta_path = run_dir / "run_meta.json"
    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta["post_game_status"] = post_game_status
    meta["alert_count"] = alert_count
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def record_run_failure(run_dir: Path, *, error: str, run_id: str | None = None) -> None:
    """写入 run_meta.json 的失败状态，供 observability run_failed 规则消费。"""
    run_dir = Path(run_dir)
    meta_path = run_dir / "run_meta.json"
    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta["status"] = "failed"
    meta["error"] = error
    if run_id:
        meta["run_id"] = run_id
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
