"""结果贡献分：归因到个人，避免「同阵营人人加分」。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp
from llm_werewolf.game_runtime.types.enums import Camp


def _eliminations_by_round(
    events: list[dict[str, Any]],
) -> dict[int, str]:
    out: dict[int, str] = {}
    for event in events:
        if event.get("event_type") != "player_eliminated":
            continue
        rnd = int(event.get("round_number", 0))
        pid = str((event.get("data") or {}).get("player_id", ""))
        if pid:
            out[rnd] = pid
    return out


def _votes_by_round(events: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    by_round: dict[int, dict[str, str]] = defaultdict(dict)
    for event in events:
        if event.get("event_type") != "vote_cast":
            continue
        rnd = int(event.get("round_number", 0))
        data = event.get("data") or {}
        voter = str(data.get("voter_id", ""))
        target = str(data.get("target_id", ""))
        if voter and target:
            by_round[rnd][voter] = target
    return dict(by_round)


def _vote_helped_camp(voter_camp: str | None, target_id: str, ctx: RunContext) -> bool:
    target_camp = target_id_to_camp(target_id, ctx.roster)
    if not voter_camp or not target_camp:
        return False
    if voter_camp == Camp.WEREWOLF.value:
        return target_camp == Camp.VILLAGER.value
    if voter_camp == Camp.VILLAGER.value:
        return target_camp == Camp.WEREWOLF.value
    return False


def _kills_by_round(events: list[dict[str, Any]]) -> dict[int, str]:
    out: dict[int, str] = {}
    for event in events:
        if event.get("event_type") != "werewolf_killed":
            continue
        rnd = int(event.get("round_number", 0))
        target = str((event.get("data") or {}).get("target_id", ""))
        if target:
            out[rnd] = target
    return out


def build_outcome_scores(
    ctx: RunContext,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """仅基于 outcome 维度事件：投票、出局、刀口、胜负（不含发言/意向）。"""
    scoped = events if events is not None else ctx.events
    elim_by_round = _eliminations_by_round(scoped)
    votes_by_round = _votes_by_round(scoped)
    winner = ctx.winner_camp

    death_round: dict[str, int] = {}
    for event in scoped:
        etype = event.get("event_type")
        if etype not in {"player_died", "player_eliminated"}:
            continue
        pid = str((event.get("data") or {}).get("player_id", ""))
        if pid:
            death_round[pid] = int(event.get("round_number", 0))

    max_round = max(
        [int(e.get("round_number", 0)) for e in scoped] + [0],
    )

    scores: dict[str, dict[str, Any]] = {}

    for pid, entry in ctx.roster.items():
        camp = entry.camp
        attributed_vote = 0
        vote_detail: list[str] = []

        for rnd, elim_target in elim_by_round.items():
            voter_target = votes_by_round.get(rnd, {}).get(pid)
            if not voter_target or voter_target != elim_target:
                continue
            if _vote_helped_camp(camp, elim_target, ctx):
                attributed_vote += 25
                vote_detail.append(f"R{rnd}:vote_elim")

        # 刀口个人归因见 wolf_night 维度；outcome 只记票型/存活/胜负
        attributed_kill = 0
        kill_detail: list[str] = []

        died_at = death_round.get(pid)
        survival = 0
        if died_at is None:
            survival = 5 + min(max_round, 5)
        elif died_at >= max_round - 1:
            survival = 3

        team_outcome = 0
        if winner and camp and winner == camp:
            team_outcome = 8

        total = attributed_vote + attributed_kill + survival + team_outcome
        scores[pid] = {
            "attributed_vote": attributed_vote,
            "attributed_kill": attributed_kill,
            "survival": survival,
            "team_outcome": team_outcome,
            "total": total,
            "details": vote_detail + kill_detail,
        }

    return scores
