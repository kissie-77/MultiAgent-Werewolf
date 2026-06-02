"""MVP 综合量化：公开说服 + 策略执行 + 结果贡献 + 狼队夜间。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from pathlib import Path
from datetime import datetime, timezone

import yaml

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.evaluation.post_game.scoring.outcome import build_outcome_scores
from llm_werewolf.evaluation.post_game.scoring.strategy import build_strategy_scores
from llm_werewolf.evaluation.post_game.scoring.wolf_night import build_wolf_night_scores
from llm_werewolf.evaluation.post_game.scoring.score_contexts import (
    DIM_OUTCOME,
    DIM_STRATEGY,
    DIM_PERSUASION,
    DIM_WOLF_NIGHT,
    write_score_contexts,
    build_score_context_bundles,
)

if TYPE_CHECKING:
    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport


def _role_key(role_name: str | None) -> str:
    if not role_name:
        return "default"
    return PromptManager.get_prompt_role_key(role_name)


def _load_role_weights() -> dict[str, dict[str, float]]:
    path = Path(__file__).with_name("role_weights.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(k): {str(dim): float(v) for dim, v in (vals or {}).items()} for k, vals in raw.items()
    }


def _weights_for_role(
    weights_table: dict[str, dict[str, float]], role_key: str, *, has_vote_intentions: bool
) -> dict[str, float]:
    """按身份取权重；无意向数据时把 persuasion 权重重分给 strategy/outcome 并归一化。"""
    w = dict(weights_table.get(role_key) or weights_table.get("default", {}))
    if not has_vote_intentions:
        extra = float(w.pop(DIM_PERSUASION, 0.0))
        w[DIM_STRATEGY] = float(w.get(DIM_STRATEGY, 0.0)) + extra * 0.5
        w[DIM_OUTCOME] = float(w.get(DIM_OUTCOME, 0.0)) + extra * 0.5
    total = sum(float(v) for v in w.values())
    if total <= 0:
        return w
    return {k: float(v) / total for k, v in w.items()}


def _persuasion_from_intention(
    intention_payload: dict[str, Any] | None, camp_report: CampPersuasionReport
) -> dict[str, dict[str, Any]]:
    by_player: dict[str, dict[str, Any]] = {}
    speeches = (intention_payload or {}).get("speeches") or []
    for item in speeches:
        pid = str(item.get("speaker_id", ""))
        if not pid:
            continue
        aligned = int(item.get("camp_aligned_score", 0))
        swing_final = int(item.get("swing_to_final_vote", 0))
        net = int(item.get("persuasion_net", 0))
        drive = int(item.get("elimination_drive_swings", 0))
        matched = bool(item.get("matched_elimination"))
        activity = aligned + swing_final + drive
        confidence = min(1.0, activity / 30.0) if activity else 0.35
        score = min(
            120.0,
            (aligned * 6 + swing_final * 12 + net * 4 + drive * 8 + (25 if matched else 0))
            * max(confidence, 0.35),
        )
        row = by_player.setdefault(pid, {"total": 0.0, "speeches": [], "golden": []})
        row["total"] += score
        excerpt = ""
        for speech in camp_report.speeches:
            if speech.speaker_id == pid and speech.round_number == item.get("round_number"):
                excerpt = speech.public_speech[:300]
                break
        row["speeches"].append({
            "round_number": item.get("round_number"),
            "score": score,
            "matched_elimination": matched,
        })
        if score >= 25 and excerpt:
            row["golden"].append({
                "kind": "public_persuasion",
                "round_number": item.get("round_number"),
                "excerpt": excerpt,
                "score": score,
                "matched_elimination": matched,
            })
    return by_player


def _mvp_eligible(entry: Any) -> bool:
    return bool(getattr(entry, "role_name", None) and getattr(entry, "camp", None))


def _normalize_within_role(raw_by_player: dict[str, float], ctx: RunContext) -> dict[str, float]:
    groups: dict[str, list[str]] = {}
    for pid, entry in ctx.roster.items():
        if not _mvp_eligible(entry):
            continue
        rk = _role_key(entry.role_name)
        groups.setdefault(rk, []).append(pid)

    normalized: dict[str, float] = {}
    for pids in groups.values():
        vals = [raw_by_player.get(pid, 0.0) for pid in pids]
        lo, hi = min(vals), max(vals)
        for pid, val in zip(pids, vals, strict=True):
            if hi > lo:
                normalized[pid] = round((val - lo) / (hi - lo) * 100, 1)
            else:
                normalized[pid] = round(val, 1)
    return normalized


def _data_quality(
    ctx: RunContext,
    intention_payload: dict[str, Any] | None,
    wolf_analysis: dict[str, Any],
    camp_report: CampPersuasionReport | None = None,
) -> dict[str, Any]:
    speeches = (intention_payload or {}).get("speeches") or []
    has_intentions = bool(speeches)
    has_wolf = bool(wolf_analysis.get("has_wolf_channel"))
    speech_count = len(speeches)
    distinct_rounds = len({s.get("round_number") for s in speeches if s.get("round_number")})

    if has_intentions and speech_count >= 6 and distinct_rounds >= 2:
        confidence = "high"
    elif has_intentions and speech_count >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    limitations: list[str] = []
    if distinct_rounds < 2:
        limitations.append("完整白天讨论不足 2 轮，说服分样本偏少")
    if camp_report and not any(s.public_speech.strip() for s in camp_report.speeches):
        limitations.append("缺少有效公开发言")

    return {
        "has_vote_intentions": has_intentions,
        "has_wolf_team_channel": has_wolf,
        "speech_count": speech_count,
        "distinct_day_rounds": distinct_rounds,
        "confidence": confidence,
        "limitations": limitations,
    }


def build_mvp_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_payload: dict[str, Any] | None = None,
    score_context_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundles = build_score_context_bundles(ctx)
    persuasion_raw = _persuasion_from_intention(intention_payload, camp_report)
    strategy_raw = build_strategy_scores(ctx, events=bundles[DIM_STRATEGY].events)
    outcome_raw = build_outcome_scores(ctx, events=bundles[DIM_OUTCOME].events)
    wolf_analysis = build_wolf_night_scores(
        ctx, wolf_records=bundles[DIM_WOLF_NIGHT].vote_intention_records
    )
    weights_table = _load_role_weights()
    dq = _data_quality(ctx, intention_payload, wolf_analysis, camp_report)

    if score_context_manifest is None:
        score_context_manifest = write_score_contexts(ctx)
    paths = score_context_manifest.get("paths") or {}

    dim_raw: dict[str, dict[str, float]] = {
        DIM_PERSUASION: {},
        DIM_STRATEGY: {},
        DIM_OUTCOME: {},
        DIM_WOLF_NIGHT: {},
    }
    player_rows: list[dict[str, Any]] = []

    for pid, entry in ctx.roster.items():
        p_total = persuasion_raw.get(pid, {}).get("total", 0.0)
        s_total = float(strategy_raw.get(pid, {}).get("total", 0))
        o_total = float(outcome_raw.get(pid, {}).get("total", 0))
        w_total = float(wolf_analysis.get("by_player", {}).get(pid, {}).get("total", 0))
        dim_raw[DIM_PERSUASION][pid] = p_total
        dim_raw[DIM_STRATEGY][pid] = s_total
        dim_raw[DIM_OUTCOME][pid] = o_total
        dim_raw[DIM_WOLF_NIGHT][pid] = w_total

    dim_norm = {dim: _normalize_within_role(vals, ctx) for dim, vals in dim_raw.items()}

    for pid, entry in ctx.roster.items():
        rk = _role_key(entry.role_name)
        w = _weights_for_role(weights_table, rk, has_vote_intentions=dq["has_vote_intentions"])

        breakdown_norm = {
            DIM_PERSUASION: dim_norm[DIM_PERSUASION].get(pid, 0.0),
            DIM_STRATEGY: dim_norm[DIM_STRATEGY].get(pid, 0.0),
            DIM_OUTCOME: dim_norm[DIM_OUTCOME].get(pid, 0.0),
            DIM_WOLF_NIGHT: dim_norm[DIM_WOLF_NIGHT].get(pid, 0.0),
        }
        breakdown_raw = {
            DIM_PERSUASION: dim_raw[DIM_PERSUASION].get(pid, 0.0),
            DIM_STRATEGY: dim_raw[DIM_STRATEGY].get(pid, 0.0),
            DIM_OUTCOME: dim_raw[DIM_OUTCOME].get(pid, 0.0),
            DIM_WOLF_NIGHT: dim_raw[DIM_WOLF_NIGHT].get(pid, 0.0),
        }
        mvp_total = round(sum(breakdown_norm[k] * w.get(k, 0.0) for k in breakdown_norm), 1)

        golden = list(persuasion_raw.get(pid, {}).get("golden", []))
        for sp in wolf_analysis.get("speeches", []):
            if sp.get("speaker_id") == pid and sp.get("total", 0) >= 10:
                golden.append({
                    "kind": "wolf_night_plan",
                    "round_number": sp.get("round_number"),
                    "excerpt": (sp.get("public_speech") or "")[:300],
                    "score": sp.get("total"),
                    "kill_match_bonus": sp.get("kill_match_bonus"),
                })

        evidence: list[dict[str, Any]] = []
        for detail in strategy_raw.get(pid, {}).get("details", []):
            evidence.append({"kind": "strategy", "why": detail})
        for detail in outcome_raw.get(pid, {}).get("details", []):
            evidence.append({"kind": "outcome", "why": detail})

        player_rows.append({
            "player_id": pid,
            "player_name": entry.player_name,
            "role_name": entry.role_name,
            "prompt_role_key": rk,
            "camp": entry.camp,
            "mvp_total": mvp_total,
            "breakdown_raw": breakdown_raw,
            "breakdown_norm": breakdown_norm,
            "weights_applied": w,
            "golden_speech_candidates": sorted(
                golden, key=lambda g: g.get("score", 0), reverse=True
            )[:5],
            "top_evidence": evidence[:8],
        })

    player_rows.sort(key=lambda r: r["mvp_total"], reverse=True)
    for idx, row in enumerate(player_rows, start=1):
        row["rank"] = idx

    mvp_row = next(
        (row for row in player_rows if row.get("role_name") and row.get("camp")),
        player_rows[0] if player_rows else None,
    )
    camp_mvp: dict[str, dict[str, Any]] = {}
    for camp in (Camp.WEREWOLF.value, Camp.VILLAGER.value):
        camp_players = [r for r in player_rows if r.get("camp") == camp]
        if camp_players:
            camp_mvp[camp] = camp_players[0]

    paths = (score_context_manifest or {}).get("paths") or {}

    return {
        "schema": "mvp_scores_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "mvp": mvp_row,
        "camp_mvp": camp_mvp,
        "players": player_rows,
        "wolf_night_analysis": {
            "has_wolf_channel": wolf_analysis.get("has_wolf_channel"),
            "speeches": wolf_analysis.get("speeches", [])[:8],
        },
        "data_quality": dq,
        "dimension_context_paths": paths,
        "selection_policy": {
            "overall": "highest_mvp_total_any_camp",
            "note": "全场 MVP 可为败方；各维度评分与复盘 LLM 仅使用 views/score_contexts 中对应材料",
        },
    }


def write_mvp_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_payload: dict[str, Any] | None = None,
    score_context_manifest: dict[str, Any] | None = None,
) -> Path:
    manifest = score_context_manifest or write_score_contexts(ctx)
    payload = build_mvp_scores(
        ctx, camp_report, intention_payload=intention_payload, score_context_manifest=manifest
    )
    path = ctx.run_dir / "mvp_scores.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
