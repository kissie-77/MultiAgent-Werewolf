"""收益分（Benefit Score）：Phase 1 完整规则项，供 MVP 合成引用。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp
from llm_werewolf.evaluation.post_game.scoring.models import PlayerBenefitScore
from llm_werewolf.game_runtime.types.enums import Camp

_NIGHT_ACTION_TYPES = frozenset({
    "seer_checked",
    "witch_saved",
    "witch_poisoned",
    "guard_protected",
    "werewolf_killed",
})


def _eliminations(ctx: RunContext) -> list[tuple[int, str, str | None]]:
    rows: list[tuple[int, str, str | None]] = []
    for event in ctx.events:
        if event.get("event_type") != "player_eliminated":
            continue
        rnd = int(event.get("round_number", 0))
        data = event.get("data") or {}
        pid = str(data.get("player_id", ""))
        role = data.get("role")
        camp = target_id_to_camp(pid, ctx.roster) if pid in ctx.roster else None
        if pid:
            rows.append((rnd, pid, camp))
    return rows


def _elimination_aligned_for_player(
    player_id: str,
    player_camp: str | None,
    eliminations: list[tuple[int, str, str | None]],
) -> int:
    if not player_camp or player_camp == Camp.NEUTRAL.value:
        return 0
    score = 0
    for _rnd, _pid, target_camp in eliminations:
        if not target_camp:
            continue
        if player_camp == Camp.WEREWOLF.value and target_camp == Camp.VILLAGER.value:
            score += 20
        elif player_camp == Camp.VILLAGER.value and target_camp == Camp.WEREWOLF.value:
            score += 20
    return score


def _eliminated_player_ids(ctx: RunContext) -> set[str]:
    out: set[str] = set()
    for event in ctx.events:
        if event.get("event_type") != "player_eliminated":
            continue
        pid = str((event.get("data") or {}).get("player_id", ""))
        if pid:
            out.add(pid)
    return out


def _survival_bonus(ctx: RunContext, player_id: str, eliminated: set[str]) -> int:
    if player_id in eliminated:
        return 0
    if ctx.winner_camp:
        return 25
    return 10


def _strategy_night_bonus(ctx: RunContext, player_id: str) -> int:
    count = 0
    for event in ctx.events:
        if str(event.get("event_type", "")) not in _NIGHT_ACTION_TYPES:
            continue
        data = event.get("data") or {}
        actor = str(data.get("player_id") or data.get("voter_id") or "")
        if actor == player_id and data.get("target_id"):
            count += 1
    return count * 8


def build_benefit_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_by_player: dict[str, int] | None = None,
) -> dict[str, Any]:
    eliminations = _eliminations(ctx)
    eliminated_ids = _eliminated_player_ids(ctx)
    winner = ctx.winner_camp
    players: list[PlayerBenefitScore] = []

    persuasion_by_speaker = {
        s.speaker_id: s.camp_aligned_score for s in camp_report.speeches
    }

    for pid, entry in ctx.roster.items():
        camp = entry.camp
        game_won = 50 if winner and camp and winner == camp else 0
        elim_aligned = _elimination_aligned_for_player(pid, camp, eliminations)
        persuasion = persuasion_by_speaker.get(pid, 0)
        survival = _survival_bonus(ctx, pid, eliminated_ids)
        strategy_night = _strategy_night_bonus(ctx, pid)
        breakdown = {
            "game_won": game_won,
            "elimination_aligned": elim_aligned,
            "camp_persuasion_sum": persuasion,
            "survival_at_end": survival,
            "strategy_night_actions": strategy_night,
        }
        total = game_won + elim_aligned + persuasion + survival + strategy_night
        players.append(
            PlayerBenefitScore(
                player_id=pid,
                player_name=entry.player_name,
                role_name=entry.role_name,
                camp=camp,
                game_won=game_won,
                elimination_aligned=elim_aligned,
                camp_persuasion_sum=persuasion,
                total=total,
                breakdown=breakdown,
            )
        )

    return {
        "schema": "benefit_scores_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "phase": "v1_complete",
        "implemented_metrics": [
            "game_won",
            "elimination_aligned",
            "camp_persuasion_sum",
            "survival_at_end",
            "strategy_night_actions",
        ],
        "players": [p.to_dict() for p in players],
        "note": "规则层收益分；已并入 mvp_scores 的 benefit 维度（与 outcome 部分相关，权重较低）",
        "intention_by_player_ref": intention_by_player or {},
    }


def write_benefit_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_by_player: dict[str, int] | None = None,
) -> dict[str, Any]:
    payload = build_benefit_scores(
        ctx,
        camp_report,
        intention_by_player=intention_by_player,
    )
    path = ctx.run_dir / "benefit_scores.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
