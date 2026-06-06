"""解析 PostGame 产物中的监控信号。"""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def load_post_game_signals(run_dir: Path) -> dict[str, Any]:
    """从 post_game_steps / post_game_analysis / run_meta 提取信号。"""
    run_dir = Path(run_dir)
    signals: dict[str, Any] = {
        "post_game_status": "skipped",
        "failed_steps": [],
        "pipeline_error": None,
        "analysis_mode": None,
        "step_summary": {},
    }

    steps_payload = _read_json(run_dir / "post_game_steps.json")
    if steps_payload:
        signals["post_game_status"] = "ok"
        steps = steps_payload.get("steps") or []
        failed = [
            step.get("step_id")
            for step in steps
            if isinstance(step, dict) and step.get("status") == "failed"
        ]
        signals["failed_steps"] = [step_id for step_id in failed if step_id]
        signals["step_summary"] = steps_payload.get("summary") or {}
        if signals["failed_steps"]:
            signals["post_game_status"] = "failed"

    manifest = _read_json(run_dir / "post_game_manifest.json")
    if manifest and signals["post_game_status"] == "skipped":
        signals["post_game_status"] = "ok"

    analysis = _read_json(run_dir / "post_game_analysis.json")
    if analysis:
        mode = analysis.get("mode")
        signals["analysis_mode"] = mode
        if mode == "failed":
            signals["post_game_status"] = "failed"

    meta = _read_json(run_dir / "run_meta.json")
    if meta:
        if meta.get("post_game_status"):
            signals["post_game_status"] = str(meta["post_game_status"])
        if meta.get("error") and not steps_payload:
            signals["pipeline_error"] = str(meta["error"])

    return signals


def derive_post_game_status(
    *,
    result_ok: bool,
    error: str | None,
    stage_errors: dict[str, str] | None = None,
) -> str:
    """由 PostGameResult 推导 post_game_status。"""
    if error:
        return "failed"
    if stage_errors:
        return "failed"
    return "ok" if result_ok else "failed"
