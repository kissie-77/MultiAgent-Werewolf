"""B1 wolf-probability calibration metrics from beliefs.jsonl."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext


def _load_belief_rows(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "beliefs.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _seat_truth(seat_roles: dict[int, str], seat: int) -> float | None:
    role = seat_roles.get(seat)
    if role is None:
        return None
    return 1.0 if role.lower() in {"werewolf", "wolf", "bloodmoonapostle"} else 0.0


def compute_belief_brier_scores(
    run_dir: Path,
    *,
    seat_roles: dict[int, str],
) -> dict[str, Any]:
    """Compute per-observer and aggregate Brier scores for wolf_probability."""
    rows = _load_belief_rows(run_dir)
    per_observer: dict[str, list[float]] = {}
    all_scores: list[float] = []

    for row in rows:
        observer_id = str(row.get("observer_id", ""))
        for entry in row.get("first_order") or []:
            if not isinstance(entry, dict):
                continue
            target_seat = int(entry.get("target_seat", 0) or 0)
            if target_seat <= 0:
                continue
            truth = _seat_truth(seat_roles, target_seat)
            if truth is None:
                continue
            prob = float(entry.get("wolf_probability", 0.0))
            score = (prob - truth) ** 2
            per_observer.setdefault(observer_id, []).append(score)
            all_scores.append(score)

    observer_summary = {
        observer_id: {
            "brier": round(sum(scores) / len(scores), 4),
            "samples": len(scores),
        }
        for observer_id, scores in per_observer.items()
        if scores
    }
    aggregate = round(sum(all_scores) / len(all_scores), 4) if all_scores else None
    return {
        "schema": "belief_calibration_v1",
        "aggregate_brier": aggregate,
        "sample_count": len(all_scores),
        "observers": observer_summary,
    }


def seat_roles_from_roster(roster: dict[str, Any]) -> dict[int, str]:
    """Map 1-based seat -> runtime role name for calibration truth labels."""
    seat_roles: dict[int, str] = {}
    for player_id, entry in roster.items():
        if isinstance(entry, dict):
            role = str(entry.get("role_name") or entry.get("role") or "")
            pid = str(entry.get("player_id") or player_id)
        else:
            role = str(getattr(entry, "role_name", "") or "")
            pid = str(getattr(entry, "player_id", player_id))
        match = re.search(r"(\d+)$", pid)
        seat = int(match.group(1)) if match else 0
        if seat > 0 and role:
            seat_roles[seat] = role
    return seat_roles


def write_belief_calibration(ctx: RunContext) -> Path:
    """Persist belief_calibration.json for PostGame / replay consumers."""
    seat_roles = seat_roles_from_roster(
        {pid: entry.to_dict() if hasattr(entry, "to_dict") else entry for pid, entry in ctx.roster.items()}
    )
    payload = compute_belief_brier_scores(ctx.run_dir, seat_roles=seat_roles)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["run_dir"] = str(ctx.run_dir)
    path = ctx.run_dir / "belief_calibration.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
