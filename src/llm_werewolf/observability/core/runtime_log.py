"""对局运行时日志采集（无需 agent_team 依赖 observability）。"""

from __future__ import annotations

import json
from typing import Any
import logging
from pathlib import Path
from datetime import datetime

_ROOT_LOGGER = "llm_werewolf"
_PROVIDER_KIND = "provider_429"
_STRUCTURED_KIND = "structured_invoke_gave_up"
_FALLBACK_KIND = "agent_fallback"


class RunObservabilityLogHandler(logging.Handler):
    """将 429 / structured_invoke / agent fallback 写入 run_dir/provider_events.jsonl。"""

    def __init__(self, run_dir: Path) -> None:
        super().__init__(level=logging.WARNING)
        self._run_dir = Path(run_dir)
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._run_dir / "provider_events.jsonl"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except Exception:
            return
        kind = _classify_message(message)
        if kind is None:
            return
        payload = {
            "schema": "provider_event_v1",
            "kind": kind,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "logger": record.name,
            "message": message,
        }
        if record.exc_info and record.exc_info[1] is not None:
            payload["error_type"] = type(record.exc_info[1]).__name__
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


_active_handler: RunObservabilityLogHandler | None = None


def _classify_message(message: str) -> str | None:
    lowered = message.lower()
    if "structured_invoke_gave_up" in lowered:
        return _STRUCTURED_KIND
    if "429" in message or "rate limit" in lowered or "ratelimit" in lowered:
        return _PROVIDER_KIND
    if "using fallback" in lowered or "using random fallback" in lowered:
        return _FALLBACK_KIND
    if "fallback seat=" in lowered:
        return _FALLBACK_KIND
    return None


def load_provider_events(run_dir: Path) -> list[dict[str, Any]]:
    path = Path(run_dir) / "provider_events.jsonl"
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            events.append(raw)
    return events


def count_provider_events(events: list[dict[str, Any]], kind: str) -> int:
    return sum(1 for event in events if event.get("kind") == kind)


def attach_run_log_handler(run_dir: Path) -> None:
    """绑定到 llm_werewolf 根 logger；重复调用会先 detach。"""
    global _active_handler
    detach_run_log_handler()
    handler = RunObservabilityLogHandler(run_dir)
    logging.getLogger(_ROOT_LOGGER).addHandler(handler)
    _active_handler = handler


def detach_run_log_handler() -> None:
    global _active_handler
    if _active_handler is None:
        return
    logging.getLogger(_ROOT_LOGGER).removeHandler(_active_handler)
    _active_handler = None
