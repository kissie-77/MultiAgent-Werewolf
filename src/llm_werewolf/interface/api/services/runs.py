"""Read game runs and artifacts from disk."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import contextlib

from llm_werewolf.interface.api.models.pages import ModelUsageStat
from llm_werewolf.interface.api.models.common import (
    PageMeta,
    RunDetail,
    RunSummary,
    ArtifactRef,
    PlayerBrief,
    PaginatedList,
)
from llm_werewolf.evaluation.post_game.run_context import load_run_context


def _dir_mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return None


def _scan_run_dir(path: Path, *, source: str) -> RunSummary | None:
    if not path.is_dir():
        return None
    events_path = path / "events.jsonl"
    has_replay = events_path.is_file()
    has_post_game = (path / "post_game_manifest.json").is_file()
    winner_camp: str | None = None
    player_count: int | None = None

    if has_replay:
        try:
            ctx = load_run_context(path)
            winner_camp = ctx.winner_camp
            player_count = len(ctx.roster)
        except Exception:
            pass

    return RunSummary(
        run_id=path.name,
        source=source,
        path=str(path.as_posix()),
        created_at=_dir_mtime_iso(path),
        player_count=player_count,
        winner_camp=winner_camp,
        has_post_game=has_post_game,
        has_replay=has_replay,
    )


def list_run_dirs(runs_dir: Path, eval_runs_dir: Path) -> list[RunSummary]:
    summaries: list[RunSummary] = []
    if runs_dir.is_dir():
        for child in runs_dir.iterdir():
            item = _scan_run_dir(child, source="runs")
            if item is not None:
                summaries.append(item)
    if eval_runs_dir.is_dir():
        for batch in eval_runs_dir.iterdir():
            if not batch.is_dir():
                continue
            games_dir = batch / "games"
            if games_dir.is_dir():
                for game in games_dir.iterdir():
                    item = _scan_run_dir(game, source="eval")
                    if item is not None:
                        summaries.append(item)
            else:
                item = _scan_run_dir(batch, source="eval")
                if item is not None:
                    summaries.append(item)
    summaries.sort(key=lambda r: r.created_at or "", reverse=True)
    return summaries


def paginate_runs(
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    page: int = 1,
    page_size: int = 20,
    source: str | None = None,
) -> PaginatedList[RunSummary]:
    all_runs = list_run_dirs(runs_dir, eval_runs_dir)
    if source:
        all_runs = [r for r in all_runs if r.source == source]
    total = len(all_runs)
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return PaginatedList(
        items=all_runs[start:end],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


def _list_artifacts(run_dir: Path) -> list[ArtifactRef]:
    refs: list[ArtifactRef] = []
    if not run_dir.is_dir():
        return refs
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(run_dir).as_posix()
        kind = "dir" if path.is_dir() else path.suffix.lstrip(".") or "file"
        refs.append(ArtifactRef(name=rel, path=str(path.as_posix()), kind=kind))
    return refs[:200]


def resolve_run_path(
    run_id: str,
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    source: str | None = None,
) -> Path | None:
    candidates: list[Path] = []
    if source in (None, "runs"):
        candidates.append(runs_dir / run_id)
    if source in (None, "eval"):
        candidates.append(eval_runs_dir / run_id)
        if eval_runs_dir.is_dir():
            for batch in eval_runs_dir.iterdir():
                candidates.append(batch / "games" / run_id)
                candidates.append(batch / run_id)
    for path in candidates:
        if path.is_dir() and (path / "events.jsonl").is_file():
            return path
        if path.is_dir() and any(path.iterdir()):
            return path
    return None


def get_run_detail(
    run_id: str,
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    source: str | None = None,
) -> RunDetail | None:
    path = resolve_run_path(run_id, runs_dir, eval_runs_dir, source=source)
    if path is None:
        return None

    detected_source = "eval" if "eval_runs" in path.as_posix() else "runs"
    summary = _scan_run_dir(path, source=detected_source)
    if summary is None:
        return None

    ctx = load_run_context(path)
    roster = [
        PlayerBrief(
            player_id=e.player_id,
            player_name=e.player_name,
            role_name=e.role_name,
            camp=e.camp,
        )
        for e in ctx.roster.values()
    ]

    extra: dict = {}
    manifest_path = path / "post_game_manifest.json"
    if manifest_path.is_file():
        with contextlib.suppress(json.JSONDecodeError):
            extra["post_game_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))

    return RunDetail(
        **summary.model_dump(),
        roster=roster,
        game_result_text=ctx.game_result_text,
        artifacts=_list_artifacts(path),
        extra=extra,
    )


def _load_launch_roster_models(run_dir: Path) -> dict[str, str]:
    """Read per-player model ids from launch_roster.json when event-derived roster lacks them."""
    path = run_dir / "launch_roster.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    players = raw.get("players") if isinstance(raw, dict) else None
    if not isinstance(players, list):
        return {}

    model_by_name: dict[str, str] = {}
    for item in players:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        model = item.get("model") or item.get("model_env")
        if isinstance(name, str) and name and isinstance(model, str) and model:
            model_by_name[name] = model
    return model_by_name


def aggregate_model_usage(runs_dir: Path | None = None, eval_runs_dir: Path | None = None) -> list[ModelUsageStat]:
    """Aggregate model usage from saved run rosters (best-effort)."""
    if runs_dir is None:
        runs_dir = Path("artifacts/runs")
    if eval_runs_dir is None:
        eval_runs_dir = Path("artifacts/eval_runs")

    stats: dict[str, dict] = {}
    for summary in list_run_dirs(runs_dir, eval_runs_dir):
        path = Path(summary.path)
        try:
            ctx = load_run_context(path)
        except Exception:
            continue
        winner_camp = ctx.winner_camp
        launch_models = _load_launch_roster_models(path)
        for entry in ctx.roster.values():
            model = getattr(entry, "ai_model", None) or launch_models.get(entry.player_name)
            if not model:
                continue
            bucket = stats.setdefault(model, {"runs": set(), "wins": 0})
            bucket["runs"].add(summary.run_id)
            if winner_camp and entry.camp == winner_camp:
                bucket["wins"] += 1

        mvp_path = path / "mvp_scores.json"
        if mvp_path.is_file():
            try:
                mvp_data = json.loads(mvp_path.read_text(encoding="utf-8"))
                for row in mvp_data if isinstance(mvp_data, list) else []:
                    if not isinstance(row, dict):
                        continue
                    model = row.get("ai_model") or row.get("model")
                    score = row.get("total") or row.get("score")
                    if model and isinstance(score, (int, float)):
                        bucket = stats.setdefault(str(model), {"runs": set(), "wins": 0, "mvp": []})
                        bucket.setdefault("mvp", []).append(float(score))
            except json.JSONDecodeError:
                pass

    result: list[ModelUsageStat] = []
    for model_id, bucket in stats.items():
        run_count = len(bucket.get("runs", set()))
        wins = bucket.get("wins", 0)
        mvp_scores = bucket.get("mvp", [])
        result.append(
            ModelUsageStat(
                model_id=model_id,
                display_name=model_id,
                run_count=run_count,
                win_rate=(wins / run_count) if run_count else None,
                avg_mvp=(sum(mvp_scores) / len(mvp_scores)) if mvp_scores else None,
            )
        )
    result.sort(key=lambda x: x.run_count, reverse=True)
    return result
