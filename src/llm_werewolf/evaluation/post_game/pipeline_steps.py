"""PostGame 流水线分步执行与状态记录。"""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class StepRecord:
    step_id: str
    status: str  # ok | failed | skipped
    duration_ms: float = 0.0
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
            "artifacts": self.artifacts,
        }


def write_pipeline_steps(run_dir: Path, steps: list[StepRecord]) -> Path:
    path = run_dir / "post_game_steps.json"
    payload = {
        "schema": "post_game_steps_v1",
        "steps": [s.to_dict() for s in steps],
        "summary": {
            "total": len(steps),
            "ok": sum(1 for s in steps if s.status == "ok"),
            "failed": sum(1 for s in steps if s.status == "failed"),
            "skipped": sum(1 for s in steps if s.status == "skipped"),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_step(
    steps: list[StepRecord],
    step_id: str,
    fn: Callable[[], T],
    *,
    artifacts: list[str] | None = None,
    required: bool = False,
) -> T | None:
    """执行同步步骤；失败时记录并返回 None（required=True 时重新抛出）。"""
    started = time.perf_counter()
    record = StepRecord(step_id=step_id, status="ok", artifacts=list(artifacts or []))
    try:
        value = fn()
        steps.append(record)
        return value
    except Exception as exc:
        record.status = "failed"
        record.error = f"{type(exc).__name__}: {exc}"
        steps.append(record)
        if required:
            raise
        return None
    finally:
        record.duration_ms = (time.perf_counter() - started) * 1000


async def run_step_async(
    steps: list[StepRecord],
    step_id: str,
    fn: Callable[[], Awaitable[T]],
    *,
    artifacts: list[str] | None = None,
    required: bool = False,
) -> T | None:
    """执行异步步骤。"""
    started = time.perf_counter()
    record = StepRecord(step_id=step_id, status="ok", artifacts=list(artifacts or []))
    try:
        value = await fn()
        steps.append(record)
        return value
    except Exception as exc:
        record.status = "failed"
        record.error = f"{type(exc).__name__}: {exc}"
        steps.append(record)
        if required:
            raise
        return None
    finally:
        record.duration_ms = (time.perf_counter() - started) * 1000


def skip_step(
    steps: list[StepRecord],
    step_id: str,
    reason: str,
    *,
    artifacts: list[str] | None = None,
) -> None:
    steps.append(
        StepRecord(
            step_id=step_id,
            status="skipped",
            error=reason,
            artifacts=list(artifacts or []),
        )
    )
