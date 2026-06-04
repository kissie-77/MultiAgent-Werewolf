"""分维度评分上下文：各 MVP 维度只包含对应阶段/频道的记录，禁止混用全局日志。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from dataclasses import field, dataclass

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.evaluation.log_views.filters import event_line, estimate_tokens
from llm_werewolf.evaluation.post_game.scoring.wolf_night import load_wolf_team_records

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext

DIM_PERSUASION = "persuasion"
DIM_STRATEGY = "strategy"
DIM_OUTCOME = "outcome"
DIM_WOLF_NIGHT = "wolf_night"

_DAY_PHASES = frozenset({"day_discussion", "day_voting", "sheriff_election"})

_PERSUASION_EVENT_TYPES = frozenset({
    "player_speech",
    "player_discussion",
    "vote_cast",
    "vote_result",
    "player_eliminated",
    "player_died",
    "death_announcement",
    "phase_change",
})

_STRATEGY_EVENT_TYPES = frozenset({
    "seer_checked",
    "witch_saved",
    "witch_poisoned",
    "guard_protected",
    "werewolf_killed",
    "vote_cast",
    "role_acting",
    "player_discussion",
})

_OUTCOME_EVENT_TYPES = frozenset({
    "vote_cast",
    "vote_result",
    "player_eliminated",
    "player_died",
    "game_ended",
    "werewolf_killed",
    "phase_change",
})


@dataclass
class ScoreContextBundle:
    dimension: str
    title: str
    description: str
    events: list[dict[str, Any]] = field(default_factory=list)
    vote_intention_records: list[dict[str, Any]] = field(default_factory=list)
    structured: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "title": self.title,
            "description": self.description,
            "event_count": len(self.events),
            "intention_record_count": len(self.vote_intention_records),
            "structured_keys": list(self.structured.keys()),
        }


def _wolf_ids(ctx: RunContext) -> set[str]:
    return {pid for pid, entry in ctx.roster.items() if entry.camp == Camp.WEREWOLF.value}


def _read_intentions(
    run_dir: Path, events: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    from llm_werewolf.evaluation.core.vote_swing_analysis import (
        _records_from_events,
        ensure_vote_intentions_jsonl,
    )

    ensure_vote_intentions_jsonl(run_dir, events=events)
    path = run_dir / "vote_intentions.jsonl"
    if not path.is_file():
        if events:
            return _records_from_events(events)
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    if rows:
        return rows
    if events:
        return _records_from_events(events)
    return []


def _is_public_event(event: dict[str, Any]) -> bool:
    visible = event.get("visible_to")
    if visible is not None:
        return False
    etype = str(event.get("event_type", ""))
    if etype not in _PERSUASION_EVENT_TYPES:
        return False
    phase = str(event.get("phase", ""))
    if etype == "player_discussion":
        return False
    if phase in _DAY_PHASES or etype in {"vote_cast", "vote_result", "player_speech"}:
        return True
    return phase != "night"


def _is_wolf_team_event(event: dict[str, Any], wolves: set[str]) -> bool:
    if not wolves:
        return False
    etype = str(event.get("event_type", ""))
    visible = event.get("visible_to")
    if etype == "player_discussion" and visible:
        vis = {str(v) for v in visible}
        return vis.issubset(wolves) and len(vis) >= 2
    if etype == "werewolf_killed":
        return True
    data = event.get("data") or {}
    return data.get("visibility") == "wolf_team" or data.get("channel") == "wolf_team"


def _filter_persuasion(ctx: RunContext, intentions: list[dict[str, Any]]) -> ScoreContextBundle:
    public_intentions = [
        r
        for r in intentions
        if str(r.get("channel", "public")) == "public"
        and str(r.get("phase", "")) in _DAY_PHASES | {"day_discussion", "day_voting"}
    ]
    events = [e for e in ctx.events if _is_public_event(e)]
    return ScoreContextBundle(
        dimension=DIM_PERSUASION,
        title="公开说服（白天）",
        description="仅白天公开发言、放逐投票与公开频道投票意向；不含狼队夜间讨论与私密技能。",
        events=events,
        vote_intention_records=public_intentions,
    )


def _filter_wolf_night(ctx: RunContext, intentions: list[dict[str, Any]]) -> ScoreContextBundle:
    wolves = _wolf_ids(ctx)
    wolf_intentions = [r for r in intentions if str(r.get("channel", "")) == "wolf_team"]
    if not wolf_intentions:
        wolf_intentions = load_wolf_team_records(ctx.run_dir, wolf_ids=wolves)

    events = [e for e in ctx.events if _is_wolf_team_event(e, wolves)]
    kills = [
        {
            "round_number": int(e.get("round_number", 0)),
            "target_id": (e.get("data") or {}).get("target_id"),
            "target_name": (e.get("data") or {}).get("target_name"),
        }
        for e in ctx.events
        if e.get("event_type") == "werewolf_killed"
    ]
    return ScoreContextBundle(
        dimension=DIM_WOLF_NIGHT,
        title="狼队夜间讨论",
        description="仅狼队频道发言、狼队投票意向与当晚刀口结果；不含白天公开讨论。",
        events=events,
        vote_intention_records=wolf_intentions,
        structured={"kills_by_round": kills},
    )


def _filter_strategy(ctx: RunContext) -> ScoreContextBundle:
    wolves = _wolf_ids(ctx)
    events: list[dict[str, Any]] = []
    for event in ctx.events:
        etype = str(event.get("event_type", ""))
        if etype not in _STRATEGY_EVENT_TYPES:
            continue
        if etype == "player_discussion" and not _is_wolf_team_event(event, wolves):
            continue
        events.append(event)
    return ScoreContextBundle(
        dimension=DIM_STRATEGY,
        title="角色策略执行",
        description="仅技能判定、夜间刀口、放逐投票等行为事件；不含公开发言正文。",
        events=events,
        vote_intention_records=[],
    )


def _filter_outcome(ctx: RunContext) -> ScoreContextBundle:
    events = [e for e in ctx.events if str(e.get("event_type", "")) in _OUTCOME_EVENT_TYPES]
    return ScoreContextBundle(
        dimension=DIM_OUTCOME,
        title="结果与归因",
        description="仅投票、出局、死亡、刀口与终局胜负；不含发言与意向细节。",
        events=events,
        vote_intention_records=[],
    )


def build_score_context_bundles(ctx: RunContext) -> dict[str, ScoreContextBundle]:
    intentions = _read_intentions(ctx.run_dir, ctx.events)
    return {
        DIM_PERSUASION: _filter_persuasion(ctx, intentions),
        DIM_STRATEGY: _filter_strategy(ctx),
        DIM_OUTCOME: _filter_outcome(ctx),
        DIM_WOLF_NIGHT: _filter_wolf_night(ctx, intentions),
    }


def _format_intention_rows(records: list[dict[str, Any]], *, max_rows: int = 40) -> list[str]:
    lines: list[str] = []
    for rec in records[:max_rows]:
        speaker = rec.get("speaker_name", rec.get("speaker_id", "?"))
        rnd = rec.get("round_number", "?")
        speech = str(rec.get("public_speech", ""))[:280]
        swings = rec.get("swing_count", 0)
        lines.append(f"- R{rnd} {speaker} (swings={swings}): {speech}")
    if len(records) > max_rows:
        lines.append(f"- … 另有 {len(records) - max_rows} 条未展示")
    return lines


def format_bundle_markdown(bundle: ScoreContextBundle) -> str:
    lines = [
        f"# {bundle.title}",
        "",
        bundle.description,
        "",
        f"- 事件条数: {len(bundle.events)}",
        f"- 投票意向条数: {len(bundle.vote_intention_records)}",
        "",
    ]
    if bundle.vote_intention_records:
        lines.append("## 投票意向 / 频道发言记录")
        lines.append("")
        lines.extend(_format_intention_rows(bundle.vote_intention_records))
        lines.append("")

    if bundle.structured:
        lines.append("## 结构化摘要")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(bundle.structured, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    if bundle.events:
        lines.append("## 相关事件（已过滤）")
        lines.append("")
        for event in bundle.events[-80:]:
            lines.append(event_line(event, max_len=240))
        lines.append("")

    return "\n".join(lines) + "\n"


def write_score_contexts(ctx: RunContext) -> dict[str, Any]:
    """写入 views/score_contexts/ 并返回 manifest。"""
    bundles = build_score_context_bundles(ctx)
    out_dir = ctx.run_dir / "views" / "score_contexts"
    out_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    paths: dict[str, str] = {}

    for dim, bundle in bundles.items():
        md_path = out_dir / f"{dim}.md"
        text = format_bundle_markdown(bundle)
        md_path.write_text(text, encoding="utf-8")
        json_path = out_dir / f"{dim}.json"
        json_path.write_text(
            json.dumps(
                {
                    "meta": bundle.to_dict(),
                    "events": bundle.events,
                    "vote_intention_records": bundle.vote_intention_records,
                    "structured": bundle.structured,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        rel_md = str(md_path.relative_to(ctx.run_dir))
        paths[dim] = rel_md
        entries.append({
            "dimension": dim,
            "path_md": rel_md,
            "path_json": str(json_path.relative_to(ctx.run_dir)),
            "token_estimate": estimate_tokens(text),
            **bundle.to_dict(),
        })

    manifest = {
        "schema": "score_contexts_v1",
        "policy": "each_dimension_isolated_no_global_log_for_scoring",
        "dimensions": entries,
        "paths": paths,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
