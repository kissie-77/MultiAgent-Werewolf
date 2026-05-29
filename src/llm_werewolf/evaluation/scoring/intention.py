"""意向改变分（Intention Score）增强。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp
from llm_werewolf.evaluation.scoring.models import SpeechIntentionScore


def _final_votes_by_round(events: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
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


def _swing_to_final_vote_count(
    speech_round: int,
    swings: list[Any],
    final_votes: dict[int, dict[str, str]],
) -> int:
    """发言后意向变更是否与同轮最终投票一致。"""
    votes = final_votes.get(speech_round, {})
    if not votes:
        return 0
    matched = 0
    for swing in swings:
        listener = swing.player_id
        to_target = swing.to_target_id
        if not listener or not to_target:
            continue
        if votes.get(listener) == to_target:
            matched += 1
    return matched


def _persuasion_net(speech: Any, ctx: RunContext) -> int:
    """同阵营听众的 camp_aligned swing 加权。"""
    speaker_camp = speech.speaker_camp
    if not speaker_camp:
        return 0
    total = 0
    for swing in speech.swings:
        if not swing.camp_aligned:
            continue
        listener = ctx.roster.get(swing.player_id)
        if listener and listener.camp == speaker_camp:
            total += 10
    return total


def build_intention_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
) -> dict[str, Any]:
    final_votes = _final_votes_by_round(ctx.events)
    speech_dicts: list[dict[str, Any]] = []

    for speech in camp_report.speeches:
        swing_final = _swing_to_final_vote_count(
            speech.round_number,
            speech.swings,
            final_votes,
        )
        net = _persuasion_net(speech, ctx)
        row = SpeechIntentionScore(
            speaker_id=speech.speaker_id,
            speaker_name=speech.speaker_name,
            round_number=speech.round_number,
            swing_count=speech.swing_count,
            camp_aligned_swings=speech.camp_aligned_swings,
            camp_aligned_score=speech.camp_aligned_score,
            matched_elimination=speech.matched_round_elimination,
            swing_to_final_vote=swing_final,
            persuasion_net=net,
        )
        payload = row.to_dict()
        payload["elimination_drive_swings"] = speech.elimination_drive_swings
        speech_dicts.append(payload)

    by_player: dict[str, int] = {}
    for item in speech_dicts:
        by_player[item["speaker_id"]] = (
            by_player.get(item["speaker_id"], 0) + item.get("intention_total", 0)
        )

    return {
        "schema": "intention_scores_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "speeches": speech_dicts,
        "by_player": by_player,
    }


def write_intention_scores(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
) -> Path:
    payload = build_intention_scores(ctx, camp_report)
    path = ctx.run_dir / "intention_scores.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
