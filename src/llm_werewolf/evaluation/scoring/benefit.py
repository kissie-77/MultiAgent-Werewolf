"""收益分（Benefit Score）Phase 1 占位实现。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp
from llm_werewolf.evaluation.scoring.models import PlayerBenefitScore
from llm_werewolf.game_runtime.types.enums import Camp


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


def _votes_by_round(events: list[dict]) -> dict[int, dict[str, str]]:
    """round -> {voter_id: target_id}"""
    by_round: dict[int, dict[str, str]] = {}
    for event in events:
        if event.get("event_type") != "vote_cast":
            continue
        rnd = int(event.get("round_number", 0))
        data = event.get("data") or {}
        voter = str(data.get("voter_id", ""))
        target = str(data.get("target_id", ""))
        if voter and target:
            by_round.setdefault(rnd, {})[voter] = target
    return by_round


def _elimination_aligned_for_player(
    player_id: str,
    player_camp: str | None,
    eliminations: list[tuple[int, str, str | None]],
    votes_by_round: dict[int, dict[str, str]],
) -> int:
    """仅当该玩家在同轮投票中投出被放逐的敌对阵营目标时计分（按人归因）。"""
    if not player_camp or player_camp == Camp.NEUTRAL.value:
        return 0
    score = 0
    for rnd, eliminated_id, target_camp in eliminations:
        if not target_camp:
            continue
        voter_target = votes_by_round.get(rnd, {}).get(player_id)
        if voter_target != eliminated_id:
            continue
        if player_camp == Camp.WEREWOLF.value and target_camp == Camp.VILLAGER.value:
            score += 20
        elif player_camp == Camp.VILLAGER.value and target_camp == Camp.WEREWOLF.value:
            score += 20
    return score


def build_benefit_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_by_player: dict[str, int] | None = None,
) -> dict[str, Any]:
    eliminations = _eliminations(ctx)
    votes_by_round = _votes_by_round(ctx.events)
    winner = ctx.winner_camp
    players: list[PlayerBenefitScore] = []

    persuasion_by_speaker: dict[str, int] = {}
    for speech in camp_report.speeches:
        persuasion_by_speaker[speech.speaker_id] = (
            persuasion_by_speaker.get(speech.speaker_id, 0) + speech.camp_aligned_score
        )

    for pid, entry in ctx.roster.items():
        camp = entry.camp
        game_won = 50 if winner and camp and winner == camp else 0
        elim_aligned = _elimination_aligned_for_player(
            pid,
            camp,
            eliminations,
            votes_by_round,
        )
        persuasion = persuasion_by_speaker.get(pid, 0)
        intention_part = (intention_by_player or {}).get(pid, 0)
        breakdown = {
            "game_won": game_won,
            "elimination_aligned": elim_aligned,
            "camp_persuasion_sum": persuasion,
            "intention_sum": intention_part,
        }
        total = game_won + elim_aligned + persuasion + intention_part
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
        "schema": "benefit_scores_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "phase": "partial",
        "implemented_metrics": [
            "game_won",
            "elimination_aligned",
            "camp_persuasion_sum",
            "intention_sum",
        ],
        "players": [p.to_dict() for p in players],
        "note": "Phase1 占位；intention 分见 intention_scores.json",
        "intention_by_player_ref": intention_by_player or {},
    }


def write_benefit_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_by_player: dict[str, int] | None = None,
) -> Path:
    payload = build_benefit_scores(
        ctx,
        camp_report,
        intention_by_player=intention_by_player,
    )
    path = ctx.run_dir / "benefit_scores.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
