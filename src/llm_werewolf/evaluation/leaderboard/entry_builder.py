"""Build leaderboard entries from one evaluation run directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.leaderboard.models import LeaderboardEntry

EXPERIMENT_META_FILENAME = "experiment_meta.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_experiment_meta(run_dir: str | Path) -> dict[str, Any]:
    path = Path(run_dir) / EXPERIMENT_META_FILENAME
    if not path.is_file():
        return {}
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def build_experiment_meta(
    run_dir: str | Path,
    *,
    version_id: str | None = None,
    model: str = "unknown",
    prompt_version: str = "v1",
    skill_version: str = "v1",
    scenario: str = "unknown",
    notes: list[str] | None = None,
    previous_run_dir: str | None = None,
    previous_skill_snapshot_path: str | None = None,
    role_version_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from llm_werewolf.strategy.role_version_manifest import get_active_manifest

    manifest = get_active_manifest()
    return {
        "schema": "experiment_meta_v2",
        "run_dir": str(Path(run_dir)),
        "version_id": version_id,
        "model": model,
        "prompt_version": prompt_version,
        "skill_version": skill_version,
        "scenario": scenario,
        "notes": notes or [],
        "previous_run_dir": previous_run_dir,
        "previous_skill_snapshot_path": previous_skill_snapshot_path,
        "role_version_manifest": role_version_manifest or manifest.to_dict(),
        "prompt_versions": dict(manifest.prompt_versions),
        "skill_versions": dict(manifest.skill_versions),
    }


def write_experiment_meta(
    run_dir: str | Path,
    *,
    version_id: str | None = None,
    model: str = "unknown",
    prompt_version: str = "unknown",
    skill_version: str = "baseline",
    scenario: str = "unknown",
    notes: list[str] | None = None,
    previous_run_dir: str | None = None,
    previous_skill_snapshot_path: str | None = None,
) -> Path:
    path = Path(run_dir) / EXPERIMENT_META_FILENAME
    payload = build_experiment_meta(
        run_dir,
        version_id=version_id,
        model=model,
        prompt_version=prompt_version,
        skill_version=skill_version,
        scenario=scenario,
        notes=notes,
        previous_run_dir=previous_run_dir,
        previous_skill_snapshot_path=previous_skill_snapshot_path,
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def infer_previous_run_dir(run_dir: str | Path) -> str | None:
    current_run_dir = Path(run_dir).resolve()
    parent = current_run_dir.parent
    if not parent.is_dir():
        return None

    candidates: list[Path] = []
    for sibling in parent.iterdir():
        if not sibling.is_dir() or sibling.resolve() == current_run_dir:
            continue
        if not _looks_like_run_dir(sibling):
            continue
        candidates.append(sibling)

    if not candidates:
        return None

    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return str(candidates[0])


def build_entry(
    run_dir: str | Path,
    *,
    version_id: str | None = None,
    model: str = "unknown",
    prompt_version: str = "unknown",
    skill_version: str = "baseline",
    scenario: str = "unknown",
    notes: list[str] | None = None,
) -> LeaderboardEntry:
    base = Path(run_dir)
    summary = load_json(base / "summary.json")
    manifest = load_json(base / "manifest.json") if (base / "manifest.json").is_file() else {}
    meta = load_experiment_meta(base)
    scenarios = manifest.get("scenarios") or []
    resolved_scenario = _resolve_value(scenario, meta.get("scenario"), "unknown")
    if resolved_scenario == "unknown" and scenarios:
        resolved_scenario = str(scenarios[0].get("name") or "unknown")
    resolved_version_id = _resolve_value(version_id, meta.get("version_id"), base.name)
    resolved_model = _resolve_value(model, meta.get("model"), "unknown")
    resolved_prompt_version = _resolve_value(prompt_version, meta.get("prompt_version"), "unknown")
    resolved_skill_version = _resolve_value(skill_version, meta.get("skill_version"), "baseline")
    resolved_notes = notes if notes is not None else list(meta.get("notes") or [])

    avg_mvp = _average_metric_from_games(base, "mvp_scores.json", ("summary", "mvp_score"))
    avg_benefit = _average_metric_from_games(base, "benefit_scores.json", ("summary", "total_score"))
    avg_intention = _average_metric_from_games(base, "intention_scores.json", ("summary", "avg_score"))

    winner_stats = _winner_stats(base)
    entry = LeaderboardEntry(
        schema="leaderboard_entry_v1",
        version_id=resolved_version_id,
        model=resolved_model,
        prompt_version=resolved_prompt_version,
        skill_version=resolved_skill_version,
        scenario=resolved_scenario,
        games=int(summary.get("total_games", 0)),
        completed_games=int(summary.get("completed_games", 0)),
        completion_rate=float(summary.get("completion_rate", 0.0)),
        win_rate=winner_stats["win_rate"],
        avg_rounds=float(summary.get("avg_rounds_per_game", 0.0)),
        avg_mvp_score=avg_mvp,
        avg_benefit_score=avg_benefit,
        avg_intention_score=avg_intention,
        information_leak_count=int(summary.get("information_leak_count", 0)),
        phase_order_violation_count=int(summary.get("phase_order_violation_count", 0)),
        role_skill_violation_count=int(summary.get("role_skill_violation_count", 0)),
        top_errors=list(summary.get("top_errors", [])),
        source_run_dir=str(base),
        notes=resolved_notes,
    )
    return entry


def write_entry(run_dir: str | Path, entry: LeaderboardEntry) -> Path:
    path = Path(run_dir) / "leaderboard_entry.json"
    path.write_text(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_entry_bundle(
    run_dir: str | Path,
    entry: LeaderboardEntry,
    *,
    previous_run_dir: str | None = None,
    previous_skill_snapshot_path: str | None = None,
) -> tuple[Path, Path]:
    entry_path = write_entry(run_dir, entry)
    resolved_previous_run_dir = previous_run_dir or infer_previous_run_dir(run_dir)
    meta_path = write_experiment_meta(
        run_dir,
        version_id=entry.version_id,
        model=entry.model,
        prompt_version=entry.prompt_version,
        skill_version=entry.skill_version,
        scenario=entry.scenario,
        notes=entry.notes,
        previous_run_dir=resolved_previous_run_dir,
        previous_skill_snapshot_path=previous_skill_snapshot_path,
    )
    return entry_path, meta_path


def _average_metric_from_games(
    base: Path,
    filename: str,
    path: tuple[str, ...],
) -> float | None:
    games_dir = base / "games"
    if not games_dir.is_dir():
        return None
    values: list[float] = []
    for game_dir in games_dir.iterdir():
        if not game_dir.is_dir():
            continue
        target = game_dir / filename
        if not target.is_file():
            continue
        payload = load_json(target)
        current: Any = payload
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if isinstance(current, (int, float)):
            values.append(float(current))
    if not values:
        return None
    return sum(values) / len(values)


def _winner_stats(base: Path) -> dict[str, float]:
    games_dir = base / "games"
    if not games_dir.is_dir():
        return {"win_rate": 0.0}
    total = 0
    wins = 0
    for game_dir in games_dir.iterdir():
        if not game_dir.is_dir():
            continue
        manifest = game_dir / "post_game_manifest.json"
        if not manifest.is_file():
            continue
        payload = load_json(manifest)
        context = payload.get("context") or {}
        winner_camp = str(context.get("winner_camp") or "")
        total += 1
        if winner_camp:
            wins += 1
    if total == 0:
        return {"win_rate": 0.0}
    return {"win_rate": wins / total}


def _resolve_value(explicit: str | None, meta_value: Any, default: str) -> str:
    if explicit is not None and explicit != default:
        return explicit
    if isinstance(meta_value, str) and meta_value.strip():
        return meta_value.strip()
    if explicit is not None:
        return explicit
    return default


def _looks_like_run_dir(path: Path) -> bool:
    if (path / "skill_snapshot.json").is_file():
        return True
    if (path / "summary.json").is_file() and (path / "manifest.json").is_file():
        return True
    return False
