"""MVP 量化：说服 + 策略 + 结果 + 狼队夜间讨论，支持败方 MVP。"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport, CampSpeechInfluence
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.evaluation.post_game.scoring.intention import build_intention_scores
from llm_werewolf.evaluation.post_game.scoring.outcome import build_outcome_scores
from llm_werewolf.evaluation.post_game.scoring.score_contexts import (
    DIM_OUTCOME,
    DIM_PERSUASION,
    DIM_STRATEGY,
    DIM_WOLF_NIGHT,
    build_score_context_bundles,
    write_score_contexts,
)
from llm_werewolf.evaluation.post_game.scoring.strategy import build_strategy_scores
from llm_werewolf.evaluation.post_game.scoring.wolf_night import build_wolf_night_scores
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.game_runtime.types.enums import Camp

_WEIGHTS_PATH = Path(__file__).with_name("role_weights.yaml")


def _load_role_weights() -> dict[str, dict[str, float]]:
    if not _WEIGHTS_PATH.is_file():
        return {}
    raw = yaml.safe_load(_WEIGHTS_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _role_key(role_name: str | None) -> str:
    if not role_name:
        return "villager"
    return PromptManager.get_prompt_role_key(role_name)


def _speech_confidence(speech: CampSpeechInfluence) -> float:
    activity = speech.camp_aligned_swings + speech.swing_count
    if activity >= 3:
        return 1.0
    if activity == 2:
        return 0.85
    if activity == 1:
        return 0.65
    return 0.4 if speech.public_speech else 0.2


def build_persuasion_scores(
    camp_report: CampPersuasionReport,
    intention_payload: dict[str, Any],
) -> dict[str, float]:
    by_player: dict[str, float] = defaultdict(float)
    intention_by = intention_payload.get("by_player") or {}

    for speech in camp_report.speeches:
        if str(getattr(speech, "phase", "")) == "night":
            continue

        conf = _speech_confidence(speech)
        points = (
            speech.camp_aligned_swings * 10
            + speech.swing_count * 3
            + (30 if speech.matched_round_elimination else 0)
        ) * conf
        by_player[speech.speaker_id] += points

    for pid, raw in intention_by.items():
        by_player[pid] += float(raw) * 0.15

    return dict(by_player)


def _rescale_weights_for_benefit(weights: dict[str, float]) -> tuple[dict[str, float], float]:
    """为 benefit 维度腾出权重（默认 0.08），其余维度同比缩放。"""
    w = dict(weights)
    benefit_w = float(w.pop("benefit", 0.08))
    if benefit_w <= 0:
        return w, 0.0
    base = sum(w.values()) or 1.0
    scale = (1.0 - benefit_w) / base
    return {k: v * scale for k, v in w.items()}, benefit_w


def _normalize_within_role(
    raw: dict[str, float],
    ctx: RunContext,
) -> dict[str, float]:
    buckets: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for pid, score in raw.items():
        entry = ctx.roster.get(pid)
        rk = _role_key(entry.role_name if entry else None)
        buckets[rk].append((pid, score))

    normed: dict[str, float] = {}
    for rk, items in buckets.items():
        if not items:
            continue
        vals = [v for _, v in items]
        lo, hi = min(vals), max(vals)
        span = hi - lo if hi > lo else 1.0
        for pid, val in items:
            normed[pid] = round((val - lo) / span * 100.0, 2)

    for pid in ctx.roster:
        if pid not in normed:
            normed[pid] = 0.0
    return normed


def _golden_speech_candidates(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    wolf_night: dict[str, Any],
    top_n: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    per_player: dict[str, list[dict[str, Any]]] = defaultdict(list)

    public_speeches = sorted(
        [s for s in camp_report.speeches if s.camp_aligned_score > 0 or s.swing_count > 0],
        key=lambda s: s.camp_aligned_score + s.swing_count * 5,
        reverse=True,
    )
    for speech in public_speeches[: top_n * 2]:
        per_player[speech.speaker_id].append(
            {
                "kind": "public_persuasion",
                "round_number": speech.round_number,
                "phase": speech.phase,
                "excerpt": (speech.public_speech or "")[:400],
                "score": speech.camp_aligned_score,
                "camp_aligned_swings": speech.camp_aligned_swings,
                "matched_elimination": speech.matched_round_elimination,
            }
        )

    for row in (wolf_night.get("speeches") or [])[: top_n * 2]:
        pid = str(row.get("speaker_id", ""))
        per_player[pid].append(
            {
                "kind": "wolf_night_plan",
                "round_number": row.get("round_number"),
                "phase": row.get("phase", "night"),
                "excerpt": (row.get("public_speech") or "")[:400],
                "score": row.get("speech_total", 0),
                "kill_match_bonus": row.get("kill_match_bonus", 0),
            }
        )

    for pid in per_player:
        per_player[pid].sort(key=lambda x: x.get("score", 0), reverse=True)
        per_player[pid] = per_player[pid][:top_n]

    return dict(per_player)


def build_mvp_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_payload: dict[str, Any] | None = None,
    score_context_manifest: dict[str, Any] | None = None,
    benefit_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    weights_table = _load_role_weights()
    if intention_payload is None:
        intention_payload = build_intention_scores(ctx, camp_report)

    bundles = build_score_context_bundles(ctx)
    if score_context_manifest is None:
        score_context_manifest = write_score_contexts(ctx)

    persuasion_raw = build_persuasion_scores(camp_report, intention_payload)
    strategy_raw = {
        pid: float(v["total"])
        for pid, v in build_strategy_scores(ctx, events=bundles[DIM_STRATEGY].events).items()
    }
    outcome_raw = {
        pid: float(v["total"])
        for pid, v in build_outcome_scores(ctx, events=bundles[DIM_OUTCOME].events).items()
    }
    wolf_night = build_wolf_night_scores(
        ctx,
        records=bundles[DIM_WOLF_NIGHT].vote_intention_records,
        outcome_events=bundles[DIM_OUTCOME].events,
    )
    wolf_raw = {pid: float(v) for pid, v in (wolf_night.get("by_player") or {}).items()}

    persuasion_norm = _normalize_within_role(persuasion_raw, ctx)
    strategy_norm = _normalize_within_role(strategy_raw, ctx)
    outcome_norm = _normalize_within_role(outcome_raw, ctx)
    wolf_norm = _normalize_within_role(wolf_raw, ctx)

    benefit_raw: dict[str, float] = {}
    if benefit_payload:
        for row in benefit_payload.get("players") or []:
            if isinstance(row, dict) and row.get("player_id"):
                benefit_raw[str(row["player_id"])] = float(row.get("total", 0))
    benefit_norm = _normalize_within_role(benefit_raw, ctx) if benefit_raw else {}

    has_intentions = bool(bundles[DIM_PERSUASION].vote_intention_records)
    players_out: list[dict[str, Any]] = []

    for pid, entry in ctx.roster.items():
        rk = _role_key(entry.role_name)
        w = weights_table.get(rk) or weights_table.get("default") or {
            "persuasion": 0.4,
            "strategy": 0.25,
            "outcome": 0.3,
            "wolf_night": 0.0,
            "benefit": 0.08,
        }
        if not has_intentions:
            w = dict(w)
            redist = w.get("persuasion", 0.4)
            w["persuasion"] = 0.0
            w["strategy"] = w.get("strategy", 0.25) + redist * 0.4
            w["outcome"] = w.get("outcome", 0.3) + redist * 0.6

        w_scaled, benefit_weight = _rescale_weights_for_benefit(w)
        weights_applied = {**w_scaled, "benefit": benefit_weight}

        mvp_total = (
            persuasion_norm.get(pid, 0) * w_scaled.get("persuasion", 0)
            + strategy_norm.get(pid, 0) * w_scaled.get("strategy", 0)
            + outcome_norm.get(pid, 0) * w_scaled.get("outcome", 0)
            + wolf_norm.get(pid, 0) * w_scaled.get("wolf_night", 0)
            + benefit_norm.get(pid, 0) * benefit_weight
        )

        players_out.append(
            {
                "player_id": pid,
                "player_name": entry.player_name,
                "role_name": entry.role_name,
                "prompt_role_key": rk,
                "camp": entry.camp,
                "mvp_total": round(mvp_total, 2),
                "breakdown_raw": {
                    "persuasion": round(persuasion_raw.get(pid, 0), 1),
                    "strategy": round(strategy_raw.get(pid, 0), 1),
                    "outcome": round(outcome_raw.get(pid, 0), 1),
                    "wolf_night": round(wolf_raw.get(pid, 0), 1),
                    "benefit": round(benefit_raw.get(pid, 0), 1),
                },
                "breakdown_norm": {
                    "persuasion": persuasion_norm.get(pid, 0),
                    "strategy": strategy_norm.get(pid, 0),
                    "outcome": outcome_norm.get(pid, 0),
                    "wolf_night": wolf_norm.get(pid, 0),
                    "benefit": benefit_norm.get(pid, 0),
                },
                "weights_applied": weights_applied,
            }
        )

    players_out.sort(key=lambda p: p["mvp_total"], reverse=True)
    for rank, row in enumerate(players_out, start=1):
        row["rank"] = rank

    mvp = players_out[0] if players_out else None
    camp_mvp: dict[str, Any] = {}
    for camp_value in (Camp.WEREWOLF.value, Camp.VILLAGER.value):
        camp_players = [p for p in players_out if p.get("camp") == camp_value]
        if camp_players:
            camp_mvp[camp_value] = camp_players[0]

    golden = _golden_speech_candidates(ctx, camp_report, wolf_night)
    for row in players_out:
        row["golden_speech_candidates"] = golden.get(row["player_id"], [])
        row["top_evidence"] = _top_evidence(row, wolf_night)

    confidence = "high" if has_intentions and len(camp_report.speeches) >= 3 else "medium"
    if not has_intentions and not ctx.events:
        confidence = "low"

    return {
        "schema": "mvp_scores_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "winner_camp": ctx.winner_camp,
        "mvp": mvp,
        "camp_mvp": camp_mvp,
        "players": players_out,
        "wolf_night_analysis": wolf_night,
        "data_quality": {
            "has_vote_intentions": has_intentions,
            "has_wolf_team_channel": wolf_night.get("has_wolf_channel", False),
            "speech_count": len(camp_report.speeches),
            "confidence": confidence,
        },
        "selection_policy": {
            "overall": "highest_mvp_total_any_camp",
            "note": "全场 MVP 可为败方；含 benefit_scores_v2 归一化维度（低权重，避免与 outcome 重复计分）",
        },
        "benefit_scores_ref": "benefit_scores.json",
        "score_context_manifest": score_context_manifest,
        "dimension_context_paths": score_context_manifest.get("paths") or {},
    }


def _top_evidence(player_row: dict[str, Any], wolf_night: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    br = player_row.get("breakdown_raw") or {}
    if br.get("persuasion", 0) > 0:
        evidence.append({"kind": "persuasion", "why": "公开讨论说服/意向摇摆"})
    if br.get("strategy", 0) > 0:
        evidence.append({"kind": "strategy", "why": "角色技能或票型执行"})
    if br.get("outcome", 0) > 0:
        evidence.append({"kind": "outcome", "why": "归因投票/存活/胜负"})
    pid = player_row.get("player_id")
    for sp in wolf_night.get("speeches") or []:
        if sp.get("speaker_id") == pid and sp.get("speech_total", 0) >= 15:
            evidence.append(
                {
                    "kind": "wolf_night",
                    "round_number": sp.get("round_number"),
                    "why": "狼队夜间讨论：计划/队友跟随/刀口匹配",
                    "excerpt": (sp.get("public_speech") or "")[:120],
                }
            )
            break
    return evidence


def write_mvp_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_payload: dict[str, Any] | None = None,
    score_context_manifest: dict[str, Any] | None = None,
    benefit_payload: dict[str, Any] | None = None,
) -> Path:
    if score_context_manifest is None:
        score_context_manifest = write_score_contexts(ctx)
    payload = build_mvp_scores(
        ctx,
        camp_report,
        intention_payload=intention_payload,
        score_context_manifest=score_context_manifest,
        benefit_payload=benefit_payload,
    )
    path = ctx.run_dir / "mvp_scores.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
