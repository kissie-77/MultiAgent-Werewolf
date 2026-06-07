"""对局运行时日志采集（无需 agent_team 依赖 observability）。"""

from __future__ import annotations

import json
import contextvars
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
        self._run_key = str(self._run_dir)

    def emit(self, record: logging.LogRecord) -> None:
        # Only capture records produced within this run's context. Each game task
        # sets its own context via set_current_run, so concurrent runs don't mix.
        if _current_run.get() != self._run_key:
            return
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


_active_handlers: dict[str, RunObservabilityLogHandler] = {}
_current_run: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ww_current_run", default=None
)


def set_current_run(run_key: str | None) -> None:
    """Tag the current async/sync context with the active run key."""
    _current_run.set(run_key)


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


def attach_run_log_handler(run_dir: Path) -> str:
    """Bind a per-run handler to the llm_werewolf root logger and mark it current.

    Returns the run key (stringified run_dir). Safe to call concurrently for
    different runs — each handler only emits for records produced within its own
    run context (see ``RunObservabilityLogHandler.emit``).
    """
    key = str(Path(run_dir))
    detach_run_log_handler(run_dir)
    handler = RunObservabilityLogHandler(run_dir)
    logging.getLogger(_ROOT_LOGGER).addHandler(handler)
    _active_handlers[key] = handler
    set_current_run(key)
    return key


def detach_run_log_handler(run_dir: Path | None = None) -> None:
    """Remove the handler for ``run_dir``; with no arg, remove all (legacy)."""
    root = logging.getLogger(_ROOT_LOGGER)
    if run_dir is None:
        for handler in list(_active_handlers.values()):
            root.removeHandler(handler)
        _active_handlers.clear()
        return
    key = str(Path(run_dir))
    handler = _active_handlers.pop(key, None)
    if handler is not None:
        root.removeHandler(handler)
