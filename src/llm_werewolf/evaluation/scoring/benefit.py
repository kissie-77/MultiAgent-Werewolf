"""收益分：与 MVP 维度对齐的 v2 实现。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

from llm_werewolf.evaluation.scoring.models import PlayerBenefitScore

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport


def build_benefit_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    intention_by_player: dict[str, int] | None = None,
    mvp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del camp_report  # MVP 已吸收 camp_persuasion 聚合

    if not mvp_payload or not mvp_payload.get("players"):
        return {
            "schema": "benefit_scores_v2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_dir": str(ctx.run_dir),
            "phase": "skipped",
            "implemented_metrics": [],
            "players": [],
            "note": "MVP 未生成，跳过收益分",
            "mvp_ref": None,
            "intention_by_player_ref": intention_by_player or {},
        }

    mvp_by_player = {
        row["player_id"]: row
        for row in (mvp_payload or {}).get("players") or []
        if row.get("player_id")
    }

    players: list[PlayerBenefitScore] = []
    for pid, entry in ctx.roster.items():
        mvp_row = mvp_by_player.get(pid, {})
        raw = mvp_row.get("breakdown_raw") or {}
        norm = mvp_row.get("breakdown_norm") or {}
        breakdown = {
            "persuasion": int(raw.get("persuasion", 0)),
            "strategy": int(raw.get("strategy", 0)),
            "outcome": int(raw.get("outcome", 0)),
            "wolf_night": int(raw.get("wolf_night", 0)),
            "mvp_total": mvp_row.get("mvp_total", 0),
            "mvp_rank": mvp_row.get("rank"),
            "intention_sum": (intention_by_player or {}).get(pid, 0),
            "breakdown_norm": norm,
        }
        total = round(float(mvp_row.get("mvp_total", 0.0)), 1)
        players.append(
            PlayerBenefitScore(
                player_id=pid,
                player_name=entry.player_name,
                role_name=entry.role_name,
                camp=entry.camp,
                game_won=0,
                elimination_aligned=int(raw.get("outcome", 0)),
                camp_persuasion_sum=int(raw.get("persuasion", 0)),
                total=total,
                breakdown=breakdown,
            )
        )

    return {
        "schema": "benefit_scores_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "phase": "mvp_integrated",
        "implemented_metrics": [
            "persuasion",
            "strategy",
            "outcome",
            "wolf_night",
            "mvp_total",
            "intention_sum",
        ],
        "players": [p.to_dict() for p in players],
        "note": "收益分已并入 MVP 量化；详见 mvp_scores.json",
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
