"""收益分：规则层 v2 + MVP 维度对齐。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

from llm_werewolf.evaluation.scoring.models import PlayerBenefitScore

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport

_WOLF_CAMPS = frozenset({"werewolf", "wolf"})
_GOOD_CAMPS = frozenset({"villager", "good"})

def _is_camp_aligned_kill(speaker_camp: str | None, target_camp: str | None) -> bool:
    if not speaker_camp or not target_camp:
        return False
    sc = speaker_camp.lower()
    tc = target_camp.lower()
    if sc in _WOLF_CAMPS:
        return tc not in _WOLF_CAMPS
    if sc in _GOOD_CAMPS or sc == "villager":
        return tc in _WOLF_CAMPS
    return False


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


_WEIGHTS = {
    "game_won": 50,
    "elimination_aligned": 15,
    "camp_persuasion": 1,
    "night_kill": 10,
    "skill_hit": 8,
    "survival": 5,
}


def _alive_at_end(ctx: RunContext) -> set[str]:
    alive = set(ctx.roster.keys())
    for event in ctx.events:
        etype = str(event.get("event_type", ""))
        pid = str((event.get("data") or {}).get("player_id", ""))
        if etype in {"player_died", "player_eliminated"} and pid:
            alive.discard(pid)
    return alive


def _persuasion_by_player(camp_report: CampPersuasionReport) -> dict[str, int]:
    totals: dict[str, int] = {}
    for speech in camp_report.speeches:
        pid = speech.speaker_id
        totals[pid] = totals.get(pid, 0) + _safe_int(speech.camp_aligned_score)
    return totals


def _elimination_aligned_by_player(camp_report: CampPersuasionReport) -> dict[str, int]:
    """发言者推动当轮对己方有利的放逐次数。"""
    totals: dict[str, int] = {}
    for speech in camp_report.speeches:
        if speech.matched_round_elimination:
            totals[speech.speaker_id] = totals.get(speech.speaker_id, 0) + 1
    return totals


def _night_kill_benefit(ctx: RunContext) -> dict[str, int]:
    """狼队夜间击杀敌对阵营：记到存活狼人（简化均分）。"""
    wolf_ids = [pid for pid, entry in ctx.roster.items() if entry.camp in _WOLF_CAMPS]
    if not wolf_ids:
        return {}
    totals: dict[str, int] = {pid: 0 for pid in wolf_ids}
    for event in ctx.events:
        if str(event.get("event_type", "")) != "werewolf_killed":
            continue
        target_id = str((event.get("data") or {}).get("player_id", ""))
        target = ctx.roster.get(target_id)
        if target and target.camp not in _WOLF_CAMPS:
            for pid in wolf_ids:
                totals[pid] = totals.get(pid, 0) + 1
    return totals


def _skill_benefit(ctx: RunContext) -> dict[str, int]:
    totals: dict[str, int] = {}
    for event in ctx.events:
        etype = str(event.get("event_type", ""))
        data = event.get("data") or {}
        actor = str(data.get("player_id") or data.get("witch_id") or data.get("seer_id") or "")
        if not actor:
            continue
        if etype == "seer_checked":
            camp = (data.get("camp") or data.get("result_camp") or "").lower()
            if camp in _WOLF_CAMPS or data.get("is_wolf") is True:
                totals[actor] = totals.get(actor, 0) + 1
        elif etype == "witch_healed":
            target_id = str(data.get("target_id") or data.get("player_id") or "")
            target = ctx.roster.get(target_id)
            if target and target.camp not in _WOLF_CAMPS:
                totals[actor] = totals.get(actor, 0) + 1
        elif etype == "witch_poisoned":
            target_id = str(data.get("target_id") or data.get("player_id") or "")
            target = ctx.roster.get(target_id)
            if target and target.camp in _WOLF_CAMPS:
                totals[actor] = totals.get(actor, 0) + 1
        elif etype == "guard_protected":
            target_id = str(data.get("target_id") or data.get("player_id") or "")
            target = ctx.roster.get(target_id)
            if target and target.camp not in _WOLF_CAMPS:
                totals[actor] = totals.get(actor, 0) + 1
        elif etype == "hunter_revenge":
            target_id = str(data.get("target_id") or "")
            target = ctx.roster.get(target_id)
            shooter = ctx.roster.get(actor)
            if shooter and target and _is_camp_aligned_kill(shooter.camp, target.camp):
                totals[actor] = totals.get(actor, 0) + 1
    return totals


def _rule_total(
    *,
    game_won: int,
    elimination_aligned: int,
    camp_persuasion_sum: int,
    night_kill: int,
    skill_hit: int,
    survival: int,
) -> float:
    return float(
        game_won * _WEIGHTS["game_won"]
        + elimination_aligned * _WEIGHTS["elimination_aligned"]
        + camp_persuasion_sum * _WEIGHTS["camp_persuasion"]
        + night_kill * _WEIGHTS["night_kill"]
        + skill_hit * _WEIGHTS["skill_hit"]
        + survival * _WEIGHTS["survival"]
    )


def build_benefit_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_by_player: dict[str, int] | None = None,
    mvp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not mvp_payload or not mvp_payload.get("players"):
        return {
            "schema": "benefit_scores_v2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_dir": str(ctx.run_dir),
            "phase": "skipped",
            "implemented_metrics": [],
            "players": [],
            "summary": {"total_score": 0.0},
            "note": "MVP 未生成，跳过收益分",
            "mvp_ref": None,
            "intention_by_player_ref": intention_by_player or {},
        }

    mvp_by_player = {
        row["player_id"]: row
        for row in (mvp_payload or {}).get("players") or []
        if row.get("player_id")
    }
    persuasion = _persuasion_by_player(camp_report)
    elim_aligned = _elimination_aligned_by_player(camp_report)
    night_kills = _night_kill_benefit(ctx)
    skill_hits = _skill_benefit(ctx)
    alive = _alive_at_end(ctx)
    winner_camp = (ctx.winner_camp or camp_report.winner_camp or "").lower()

    players: list[PlayerBenefitScore] = []
    rule_totals: list[float] = []

    for pid, entry in ctx.roster.items():
        mvp_row = mvp_by_player.get(pid, {})
        raw = mvp_row.get("breakdown_raw") or {}
        norm = mvp_row.get("breakdown_norm") or {}
        player_camp = (entry.camp or "").lower()
        game_won = int(bool(player_camp and winner_camp and player_camp == winner_camp))
        camp_persuasion_sum = _safe_int(persuasion.get(pid, 0))
        elimination_aligned = _safe_int(elim_aligned.get(pid, 0))
        night_kill = _safe_int(night_kills.get(pid, 0))
        skill_hit = _safe_int(skill_hits.get(pid, 0))
        survival = int(pid in alive)
        rule_score = _rule_total(
            game_won=game_won,
            elimination_aligned=elimination_aligned,
            camp_persuasion_sum=camp_persuasion_sum,
            night_kill=night_kill,
            skill_hit=skill_hit,
            survival=survival,
        )
        mvp_total = float(mvp_row.get("mvp_total", 0.0))
        combined = round(0.55 * mvp_total + 0.45 * min(rule_score, 100.0), 1)
        rule_totals.append(rule_score)
        breakdown = {
            "persuasion": _safe_int(raw.get("persuasion")),
            "strategy": _safe_int(raw.get("strategy")),
            "outcome": _safe_int(raw.get("outcome")),
            "wolf_night": _safe_int(raw.get("wolf_night")),
            "mvp_total": mvp_total,
            "mvp_rank": mvp_row.get("rank"),
            "intention_sum": (intention_by_player or {}).get(pid, 0),
            "game_won": game_won,
            "elimination_aligned": elimination_aligned,
            "camp_persuasion_sum": camp_persuasion_sum,
            "night_kill_benefit": night_kill,
            "skill_benefit": skill_hit,
            "survival_bonus": survival,
            "rule_total": round(rule_score, 1),
            "breakdown_norm": norm,
        }
        players.append(
            PlayerBenefitScore(
                player_id=pid,
                player_name=entry.player_name,
                role_name=entry.role_name,
                camp=entry.camp,
                game_won=game_won,
                elimination_aligned=elimination_aligned,
                camp_persuasion_sum=camp_persuasion_sum,
                total=combined,
                breakdown=breakdown,
            )
        )

    avg_rule = round(sum(rule_totals) / len(rule_totals), 4) if rule_totals else 0.0
    avg_combined = round(sum(p.total for p in players) / len(players), 4) if players else 0.0

    return {
        "schema": "benefit_scores_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "phase": "full_rules",
        "implemented_metrics": [
            "game_won",
            "elimination_aligned",
            "camp_persuasion_sum",
            "night_kill_benefit",
            "skill_benefit",
            "survival_bonus",
            "rule_total",
            "mvp_total",
            "intention_sum",
        ],
        "weights": dict(_WEIGHTS),
        "players": [p.to_dict() for p in players],
        "summary": {
            "total_score": avg_combined,
            "avg_rule_total": avg_rule,
            "winner_camp": winner_camp or None,
        },
        "note": "收益分 = 55% MVP + 45% 规则层（封顶 100）；规则层见 weights",
        "mvp_ref": (mvp_payload or {}).get("schema"),
        "intention_by_player_ref": intention_by_player or {},
    }


def write_benefit_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_by_player: dict[str, int] | None = None,
    mvp_payload: dict[str, Any] | None = None,
) -> Path:
    payload = build_benefit_scores(
        ctx, camp_report, intention_by_player=intention_by_player, mvp_payload=mvp_payload
    )
    path = ctx.run_dir / "benefit_scores.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
