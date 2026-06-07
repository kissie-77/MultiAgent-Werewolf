"""Replay, share, and game snapshot helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from pathlib import Path
from collections import Counter

from llm_werewolf.interface.api.models.pages import (
    MvpRankItem,
    GameSnapshot,
    PhaseSummary,
    ReplayPageData,
    ReplayEventItem,
    ReplayScoreBlock,
    ShareReplayPageData,
)
from llm_werewolf.interface.api.services.runs import effective_player_count, get_run_detail
from llm_werewolf.evaluation.log_views.filters import event_is_visible_to
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.turning_points import build_turning_points

if TYPE_CHECKING:
    from llm_werewolf.interface.api.models.common import PlayerBrief


def _load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _load_markdown(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _load_jsonl(path: Path, *, limit: int = 500) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
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
        if len(rows) >= limit:
            break
    return rows


def load_belief_snapshots(run_dir: Path, *, limit: int = 500) -> list[dict]:
    """Load god-view belief timeline from beliefs.jsonl."""
    return _load_jsonl(run_dir / "beliefs.jsonl", limit=limit)


def load_wolf_camp_snapshots(run_dir: Path, *, limit: int = 200) -> list[dict]:
    """Load wolf-team shared panel history."""
    return _load_jsonl(run_dir / "wolf_camp_mind.jsonl", limit=limit)


def summarize_belief_heatmap(snapshots: list[dict]) -> dict[str, Any]:
    """Summarize latest wolf-probability per observer/target seat."""
    heatmap: dict[str, dict[str, float]] = {}
    for row in snapshots:
        observer = str(row.get("observer_seat", row.get("observer_id", "")))
        bucket = heatmap.setdefault(observer, {})
        for entry in row.get("first_order") or []:
            if not isinstance(entry, dict):
                continue
            target = str(entry.get("target_seat", ""))
            bucket[target] = float(entry.get("wolf_probability", 0.0))
    return {"observers": heatmap, "snapshot_count": len(snapshots)}


_REPLAY_ONLY_EVENT_TYPES = frozenset({"vote_intention_snapshot", "belief_snapshot"})


def _event_visible_for_replay(
    event: dict[str, Any],
    *,
    view: str,
    viewer_id: str | None,
) -> bool:
    if view == "god":
        return True
    if event.get("event_type") in _REPLAY_ONLY_EVENT_TYPES:
        return False
    if viewer_id:
        return event_is_visible_to(event, viewer_id)
    return event.get("visible_to") is None


def build_timeline(
    run_dir: Path,
    *,
    limit: int = 500,
    view: str = "public",
    viewer_id: str | None = None,
) -> list[ReplayEventItem]:
    ctx = load_run_context(run_dir)
    items: list[ReplayEventItem] = []
    filtered = [
        event
        for event in ctx.events
        if _event_visible_for_replay(event, view=view, viewer_id=viewer_id)
    ][:limit]
    for idx, event in enumerate(filtered):
        items.append(
            ReplayEventItem(
                index=idx,
                event_type=str(event.get("event_type", "")),
                round_number=int(event.get("round_number", 0)),
                phase=str(event.get("phase", "")),
                message=str(event.get("message", "")),
                timestamp=str(event.get("timestamp")) if event.get("timestamp") else None,
                data=dict(event.get("data") or {}),
            )
        )
    return items


def _score_blocks(run_dir: Path) -> list[ReplayScoreBlock]:
    blocks: list[ReplayScoreBlock] = []
    mapping = {
        "mvp_scores.json": ("mvp", "MVP 评分"),
        "benefit_scores.json": ("benefit", "收益评分"),
        "intention_scores.json": ("intention", "意向一致性"),
        "camp_persuasion_summary.json": ("persuasion", "阵营说服"),
        "vote_swing_summary.json": ("swing", "投票摇摆"),
        "game_quality_report.json": ("quality", "对局质量"),
        "belief_calibration.json": ("belief_calibration", "信念校准"),
    }
    for filename, (kind, title) in mapping.items():
        payload = _load_json(run_dir / filename)
        if payload is not None:
            blocks.append(ReplayScoreBlock(kind=kind, title=title, payload={"data": payload}))
    return blocks


def get_replay_page(
    run_id: str,
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    source: str | None = None,
    view: str = "public",
    viewer_id: str | None = None,
) -> ReplayPageData | None:
    view_scope = "god" if view == "god" else "player" if viewer_id else "public"
    detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source)
    if detail is None:
        return None
    run_dir = Path(detail.path)
    views_manifest = _load_json(run_dir / "views_manifest.json")
    views_available: list[str] = []
    if isinstance(views_manifest, dict):
        views_available = list(views_manifest.keys())

    report_md = _load_markdown(run_dir / "post_game_report.md") or _load_markdown(
        run_dir / "game_quality_report.md"
    )

    return ReplayPageData(
        run=detail,
        view_scope=view_scope,
        timeline=build_timeline(run_dir, view=view, viewer_id=viewer_id),
        scores=_score_blocks(run_dir),
        views_available=views_available,
        report_markdown=report_md,
        belief_snapshots=load_belief_snapshots(run_dir) if view == "god" else [],
        wolf_camp_snapshots=load_wolf_camp_snapshots(run_dir) if view == "god" else [],
        belief_heatmap=(
            summarize_belief_heatmap(load_belief_snapshots(run_dir)) if view == "god" else {}
        ),
    )


def get_share_replay_page(
    run_id: str,
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    source: str | None = None,
) -> ShareReplayPageData | None:
    detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source)
    if detail is None:
        return None

    highlights: list[PlayerBrief] = []
    for player in detail.roster[:6]:
        highlights.append(player)

    winner_label = detail.winner_camp or "未知"
    seats = effective_player_count(
        run_id=run_id,
        player_count=detail.player_count,
        roster_size=len(detail.roster),
    )
    summary = f"{seats} 人局 · 胜方：{winner_label}"

    return ShareReplayPageData(
        run_id=run_id,
        share_title=f"AI 狼人杀复盘 · {run_id}",
        share_summary=summary,
        og_title=f"AI 狼人杀 · {winner_label} 阵营获胜",
        og_description=summary,
        winner_camp=detail.winner_camp,
        highlight_players=highlights,
        share_url_path=f"/share/{run_id}",
        artifacts=[a for a in detail.artifacts if a.name.endswith((".md", ".json"))][:10],
    )


def _last_event_field(events: list[dict], field: str, default: str | int | None = None):
    for event in reversed(events):
        val = event.get(field)
        if val is not None:
            return val
    return default


def extract_game_snapshot(run_dir: Path) -> GameSnapshot:
    ctx = load_run_context(run_dir)
    events = ctx.events
    phase = str(_last_event_field(events, "phase", "unknown"))
    round_number = int(_last_event_field(events, "round_number", 0) or 0)
    is_ended = ctx.winner_camp is not None or any(
        e.get("event_type") == "game_ended" for e in events
    )

    alive_ids: set[str] = set(ctx.roster.keys())
    for event in events:
        etype = str(event.get("event_type", ""))
        pid = (event.get("data") or {}).get("player_id")
        if etype in {"player_died", "player_eliminated"} and pid:
            alive_ids.discard(str(pid))

    sheriff_id = None
    for event in events:
        if event.get("event_type") == "sheriff_elected":
            sheriff_id = str((event.get("data") or {}).get("player_id") or "") or None

    return GameSnapshot(
        phase=phase,
        round_number=round_number,
        winner_camp=ctx.winner_camp,
        is_ended=is_ended,
        sheriff_id=sheriff_id,
        alive_count=len(alive_ids),
        dead_count=max(len(ctx.roster) - len(alive_ids), 0),
        event_count=len(events),
    )


def extract_camp_counts(run_dir: Path) -> dict[str, int]:
    ctx = load_run_context(run_dir)
    alive_ids: set[str] = set(ctx.roster.keys())
    for event in ctx.events:
        etype = str(event.get("event_type", ""))
        pid = (event.get("data") or {}).get("player_id")
        if etype in {"player_died", "player_eliminated"} and pid:
            alive_ids.discard(str(pid))

    counts: Counter[str] = Counter()
    for pid in alive_ids:
        entry = ctx.roster.get(pid)
        if entry and entry.camp:
            counts[entry.camp] += 1
    return dict(counts)


def recent_events(run_dir: Path, *, limit: int = 20) -> list[ReplayEventItem]:
    timeline = build_timeline(run_dir, limit=500)
    return timeline[-limit:]


def build_phase_summary(run_dir: Path) -> list[PhaseSummary]:
    ctx = load_run_context(run_dir)
    buckets: dict[tuple[int, str], list[str]] = {}
    for event in ctx.events:
        rnd = int(event.get("round_number", 0))
        phase = str(event.get("phase", ""))
        etype = str(event.get("event_type", ""))
        key = (rnd, phase)
        buckets.setdefault(key, []).append(etype)

    summaries: list[PhaseSummary] = []
    for (rnd, phase), types in sorted(buckets.items()):
        counter = Counter(types)
        top_types = [f"{k}×{v}" for k, v in counter.most_common(5)]
        summaries.append(
            PhaseSummary(
                round_number=rnd,
                phase=phase,
                event_count=len(types),
                highlight_event_types=top_types,
            )
        )
    return summaries


def build_mvp_ranking(run_dir: Path) -> list[MvpRankItem]:
    path = run_dir / "mvp_scores.json"
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    rows = raw if isinstance(raw, list) else raw.get("players") or raw.get("rankings") or []
    ranking: list[MvpRankItem] = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        ranking.append(
            MvpRankItem(
                rank=idx,
                player_id=str(row.get("player_id", "")),
                player_name=str(row.get("player_name", row.get("name", ""))),
                role_name=row.get("role_name") or row.get("role"),
                total_score=float(row.get("total") or row.get("score") or 0),
                ai_model=row.get("ai_model") or row.get("model"),
            )
        )
    ranking.sort(key=lambda x: x.total_score, reverse=True)
    for i, item in enumerate(ranking, start=1):
        item.rank = i
    return ranking


def build_turning_point_lines(run_dir: Path) -> list[str]:
    ctx = load_run_context(run_dir)
    lines = build_turning_points(ctx)
    return [line.lstrip("- ").strip("* ") for line in lines]
