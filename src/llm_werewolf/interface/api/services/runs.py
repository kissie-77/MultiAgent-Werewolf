"""Read game runs and artifacts from disk."""

from __future__ import annotations

import json
import re
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
from llm_werewolf.evaluation.post_game.run_context import (
    PlayerRosterEntry,
    _read_jsonl,
    load_run_context,
    roster_from_events,
    winner_from_events,
)


def _dir_mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return None


def _player_count_from_run_id(run_id: str) -> int | None:
    match = re.search(r"(?:^|[-_])(\d+)p(?:[-_]|$)", run_id, re.IGNORECASE)
    if not match:
        return None
    count = int(match.group(1))
    return count if count > 0 else None


def _player_count_from_files(run_dir: Path) -> int | None:
    god_path = run_dir / "god_roster.json"
    if god_path.is_file():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            data = json.loads(god_path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return len(data)

    launch_path = run_dir / "launch_roster.json"
    if launch_path.is_file():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            raw = json.loads(launch_path.read_text(encoding="utf-8"))
            players = raw.get("players") if isinstance(raw, dict) else None
            if isinstance(players, list) and players:
                return len(players)
    return None


def _scan_run_metadata(path: Path) -> tuple[int | None, str | None]:
    """Best-effort player_count / winner_camp from on-disk logs (no live session)."""
    events_path = path / "events.jsonl"
    player_count: int | None = None
    winner_camp: str | None = None

    if events_path.is_file():
        events = _read_jsonl(events_path)
        roster = roster_from_events(events)
        if roster:
            player_count = len(roster)
        winner_camp, _ = winner_from_events(events)

    if player_count is None or player_count <= 0:
        player_count = _player_count_from_files(path)
    if player_count is None or player_count <= 0:
        player_count = _player_count_from_run_id(path.name)

    if winner_camp is None and events_path.is_file():
        with contextlib.suppress(Exception):
            ctx = load_run_context(path)
            winner_camp = ctx.winner_camp
            if not player_count and ctx.roster:
                player_count = len(ctx.roster)

    return player_count, winner_camp


def effective_player_count(
    *,
    run_id: str,
    player_count: int | None,
    roster_size: int,
) -> int:
    """Resolve display seat count when roster parsing is incomplete."""
    inferred = _player_count_from_run_id(run_id)
    counts = [c for c in (player_count, roster_size, inferred) if isinstance(c, int) and c > 0]
    if not counts:
        return 0
    if inferred:
        return max(inferred, *counts)
    return max(counts)


def _roster_from_god_json(run_dir: Path) -> dict[str, PlayerRosterEntry]:
    god_path = run_dir / "god_roster.json"
    if not god_path.is_file():
        return {}
    with contextlib.suppress(json.JSONDecodeError, OSError):
        data = json.loads(god_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return {}
        roster: dict[str, PlayerRosterEntry] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            seat = item.get("seat")
            if not isinstance(seat, int) or seat <= 0:
                continue
            player_id = f"player_{seat}"
            roster[player_id] = PlayerRosterEntry(
                player_id=player_id,
                player_name=str(item.get("name") or f"Player{seat}"),
                role_name=item.get("role"),
                camp=item.get("camp"),
            )
        return roster
    return {}


def _load_run_roster(run_dir: Path) -> tuple[dict[str, PlayerRosterEntry], str | None]:
    """Best-effort roster + optional game_result_text from on-disk artifacts."""
    game_result_text: str | None = None
    with contextlib.suppress(Exception):
        ctx = load_run_context(run_dir)
        if ctx.roster:
            return ctx.roster, ctx.game_result_text
        game_result_text = ctx.game_result_text

    events = _read_jsonl(run_dir / "events.jsonl")
    roster = roster_from_events(events)
    if roster:
        return roster, game_result_text

    god_roster = _roster_from_god_json(run_dir)
    if god_roster:
        return god_roster, game_result_text

    return {}, game_result_text


def _scan_run_dir(path: Path, *, source: str) -> RunSummary | None:
    if not path.is_dir():
        return None
    events_path = path / "events.jsonl"
    has_replay = events_path.is_file() and events_path.stat().st_size > 0
    has_post_game = (path / "post_game_manifest.json").is_file()
    player_count, winner_camp = _scan_run_metadata(path)

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
    replay_only: bool = False,
) -> PaginatedList[RunSummary]:
    all_runs = list_run_dirs(runs_dir, eval_runs_dir)
    if source:
        all_runs = [r for r in all_runs if r.source == source]
    if replay_only:
        all_runs = [r for r in all_runs if r.has_replay]
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

    roster_map, game_result_text = _load_run_roster(path)
    roster = [
        PlayerBrief(
            player_id=e.player_id,
            player_name=e.player_name,
            role_name=e.role_name,
            camp=e.camp,
        )
        for e in roster_map.values()
    ]

    extra: dict = {}
    manifest_path = path / "post_game_manifest.json"
    if manifest_path.is_file():
        with contextlib.suppress(json.JSONDecodeError):
            extra["post_game_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))

    detail_data = summary.model_dump()
    detail_data["player_count"] = effective_player_count(
        run_id=run_id,
        player_count=detail_data.get("player_count"),
        roster_size=len(roster),
    )

    return RunDetail(
        **detail_data,
        roster=roster,
        game_result_text=game_result_text,
        artifacts=_list_artifacts(path),
        extra=extra,
    )


# Human-controlled seats are not AI models; they must not pollute the leaderboard.
_HUMAN_SEAT_MODELS = frozenset({"human", "web-human"})


def _launch_roster_models(run_dir: Path) -> dict[str, str]:
    """Map both ``player_{seat}`` ids and player names -> model from launch_roster.json.

    This is the per-seat model source for runs (the engine roster carries no model).
    It is the data source ``aggregate_model_usage`` previously failed to read, which
    left the model leaderboard empty.
    """
    path = run_dir / "launch_roster.json"
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    players = data.get("players") if isinstance(data, dict) else None
    if not isinstance(players, list):
        return out
    for seat, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            continue
        model = player.get("model")
        if not model:
            continue
        out[f"player_{seat}"] = str(model)
        name = player.get("name")
        if name:
            out.setdefault(str(name), str(model))
    return out


def _resolve_seat_model(
    player_id: str, player_name: str | None, launch_models: dict[str, str]
) -> str | None:
    """Resolve a seat's AI model, skipping human-controlled seats."""
    model = launch_models.get(player_id)
    if not model and player_name:
        model = launch_models.get(str(player_name))
    if not model or model in _HUMAN_SEAT_MODELS:
        return None
    return model


def _mvp_rows(run_dir: Path) -> list[dict]:
    """Read mvp_scores.json rows, tolerating both list and {players|rankings} shapes."""
    path = run_dir / "mvp_scores.json"
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        rows = raw.get("players") or raw.get("rankings") or []
        return [r for r in rows if isinstance(r, dict)]
    return []


def aggregate_model_usage(runs_dir: Path | None = None, eval_runs_dir: Path | None = None) -> list[ModelUsageStat]:
    """Aggregate per-model usage across saved runs (best-effort).

    The per-seat model is read from ``launch_roster.json`` (the engine roster does
    not carry it); MVP averages come from ``mvp_scores.json`` (``mvp_total``). Wins
    are counted once per run so the win rate stays in ``[0, 1]``, and human-controlled
    seats are excluded — they are not AI models.
    """
    if runs_dir is None:
        runs_dir = Path("artifacts/runs")
    if eval_runs_dir is None:
        eval_runs_dir = Path("artifacts/eval_runs")

    stats: dict[str, dict] = {}

    def _bucket(model: str) -> dict:
        return stats.setdefault(model, {"runs": 0, "wins": 0, "mvp": []})

    for summary in list_run_dirs(runs_dir, eval_runs_dir):
        path = Path(summary.path)
        roster_map, _ = _load_run_roster(path)
        if not roster_map:
            continue
        launch_models = _launch_roster_models(path)
        winner_camp = ctx.winner_camp

        models_in_run: set[str] = set()
        winners_in_run: set[str] = set()
        for entry in ctx.roster.values():
            model = getattr(entry, "ai_model", None) or _resolve_seat_model(
                entry.player_id, entry.player_name, launch_models
            )
            if not model or model in _HUMAN_SEAT_MODELS:
                continue
            models_in_run.add(model)
            if winner_camp and entry.camp == winner_camp:
                winners_in_run.add(model)
        for model in models_in_run:
            bucket = _bucket(model)
            bucket["runs"] += 1
            if model in winners_in_run:
                bucket["wins"] += 1

        for row in _mvp_rows(path):
            model = (
                row.get("ai_model")
                or row.get("model")
                or _resolve_seat_model(str(row.get("player_id", "")), row.get("player_name"), launch_models)
            )
            score = row.get("mvp_total")
            if score is None:
                score = row.get("total") or row.get("score")
            if model and model not in _HUMAN_SEAT_MODELS and isinstance(score, (int, float)):
                _bucket(str(model))["mvp"].append(float(score))

    result: list[ModelUsageStat] = []
    for model_id, bucket in stats.items():
        run_count = bucket.get("runs", 0)
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
