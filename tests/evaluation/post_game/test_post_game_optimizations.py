"""PostGame 复盘/MVP/Skill 优化回归。"""

import json
from pathlib import Path

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.evaluation.scoring.intention import build_intention_scores
from llm_werewolf.evaluation.post_game.run_context import load_run_context, target_id_to_camp
from llm_werewolf.evaluation.post_game.scoring.mvp import build_mvp_scores
from llm_werewolf.evaluation.post_game.turning_points import build_turning_points
from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.scoring.wolf_night import build_wolf_night_scores
from llm_werewolf.evaluation.post_game.game_quality_report import build_game_quality_report
from llm_werewolf.evaluation.post_game.skill_generation.skill_generation_rules import (
    evaluate_persuasion_speech,
    collect_skill_generation_candidates,
)


def test_wolf_night_parses_player_discussion_speech() -> None:
    run_dir = Path("artifacts/runs/20260529-143527")
    if not (run_dir / "events.jsonl").is_file():
        return
    ctx = load_run_context(run_dir)
    analysis = build_wolf_night_scores(ctx)
    assert analysis["has_wolf_channel"]
    assert analysis["speeches"]
    first = analysis["speeches"][0]
    assert first.get("speaker_name")
    assert first.get("public_speech")
    assert first.get("plan_clarity", 0) > 0


def test_villager_harmful_speech_not_promoted_to_skill() -> None:
    run_dir = Path("artifacts/runs/20260529-143527")
    if not (run_dir / "events.jsonl").is_file():
        return
    ctx = load_run_context(run_dir)
    camp = build_camp_persuasion_report(ctx)
    player5 = next(s for s in camp.speeches if s.speaker_id == "player_5")
    rule = evaluate_persuasion_speech(player5, ctx)
    assert not rule.passed

    candidates = collect_skill_generation_candidates(ctx, camp)
    skill_ids = {c.player_id for c in candidates if c.source_kind == "persuasion_speech"}
    assert "player_3" in skill_ids
    assert "player_5" not in skill_ids


def test_game_quality_report_has_turning_points_and_medium_confidence() -> None:
    run_dir = Path("artifacts/runs/20260529-143527")
    if not (run_dir / "events.jsonl").is_file():
        return
    ctx = load_run_context(run_dir)
    camp = build_camp_persuasion_report(ctx)
    intention = build_intention_scores(ctx, camp)
    mvp = build_mvp_scores(ctx, camp, intention_payload=intention)
    swing = json.loads((run_dir / "vote_swing_summary.json").read_text(encoding="utf-8"))
    report = build_game_quality_report(ctx, mvp, swing_summary=swing)
    md = report["markdown"]
    assert "关键转折" in md
    assert "第 1 夜" in md
    assert mvp["data_quality"]["confidence"] == "medium"
    assert "狼队夜间讨论亮点" in md
    assert "**None**" not in md


def test_mvp_player4_gets_elimination_drive_credit() -> None:
    run_dir = Path("artifacts/runs/20260529-143527")
    if not (run_dir / "events.jsonl").is_file():
        return
    ctx = load_run_context(run_dir)
    camp = build_camp_persuasion_report(ctx)
    p4 = next(s for s in camp.speeches if s.speaker_id == "player_4")
    assert p4.elimination_drive_swings >= 1
    elim_camp = (
        target_id_to_camp(p4.elimination_target_id, ctx.roster)
        if p4.elimination_target_id
        else None
    )
    assert p4.matched_round_elimination == (
        elim_camp == Camp.WEREWOLF.value and p4.elimination_drive_swings >= 1
    )

    intention = build_intention_scores(ctx, camp)
    mvp = build_mvp_scores(ctx, camp, intention_payload=intention)
    by_id = {row["player_id"]: row for row in mvp["players"]}
    assert by_id["player_3"]["mvp_total"] >= by_id["player_4"]["mvp_total"]


def test_turning_points_include_winner() -> None:
    from llm_werewolf.evaluation.post_game.run_context import RunContext

    events = [
        {
            "event_type": "game_ended",
            "round_number": 2,
            "phase": "ended",
            "data": {"winner_camp": Camp.WEREWOLF.value},
        }
    ]
    ctx = RunContext(
        run_dir=Path("."),
        events=events,
        roster={},
        winner_camp=Camp.WEREWOLF.value,
        prompt_version="v2",
    )
    points = build_turning_points(ctx)
    assert any("狼人" in p for p in points)
