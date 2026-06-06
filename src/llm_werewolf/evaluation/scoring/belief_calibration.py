"""B1 wolf-probability calibration metrics from beliefs.jsonl."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


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
