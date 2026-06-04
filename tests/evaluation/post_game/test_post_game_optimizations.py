"""PostGame 复盘/MVP/Skill 优化回归。"""

import json
from pathlib import Path

import pytest

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.evaluation.scoring.intention import build_intention_scores
from llm_werewolf.evaluation.post_game.run_context import (
    RunContext,
    PlayerRosterEntry,
    load_run_context,
    target_id_to_camp,
)
from llm_werewolf.evaluation.post_game.scoring.mvp import build_mvp_scores
from llm_werewolf.evaluation.post_game.scoring.outcome import build_outcome_scores
from llm_werewolf.evaluation.post_game.turning_points import build_turning_points
from llm_werewolf.evaluation.post_game.camp_persuasion import (
    CampPersuasionReport,
    build_camp_persuasion_report,
)
from llm_werewolf.evaluation.post_game.scoring.wolf_night import build_wolf_night_scores
from llm_werewolf.evaluation.post_game.game_quality_report import build_game_quality_report
from llm_werewolf.evaluation.post_game.skill_generation.skill_generation_rules import (
    evaluate_persuasion_speech,
    collect_skill_generation_candidates,
)


def _witch_poison_ctx(tmp_path: Path, event_type: str) -> RunContext:
    events = [
        {
            "event_type": event_type,
            "round_number": 1,
            "phase": "night",
            "message": "Witch poisoned TargetWolf",
            "data": {"player_id": "player_4", "target_id": "player_9"},
        }
    ]
    roster = {
        "player_4": PlayerRosterEntry(
            player_id="player_4",
            player_name="Witch",
            role_name="Witch",
            camp=Camp.VILLAGER.value,
        ),
        "player_9": PlayerRosterEntry(
            player_id="player_9",
            player_name="TargetWolf",
            role_name="Werewolf",
            camp=Camp.WEREWOLF.value,
        ),
    }
    return RunContext(run_dir=tmp_path, events=events, roster=roster, prompt_version="v2")


@pytest.mark.parametrize("event_type", ["witch_poisoned", "witch_poison_used"])
def test_turning_points_accept_witch_poison_aliases(tmp_path: Path, event_type: str) -> None:
    ctx = _witch_poison_ctx(tmp_path, event_type)

    points = build_turning_points(ctx)

    assert any("TargetWolf" in point for point in points)


@pytest.mark.parametrize("event_type", ["witch_poisoned", "witch_poison_used"])
def test_skill_generation_accepts_witch_poison_aliases(
    tmp_path: Path, event_type: str
) -> None:
    ctx = _witch_poison_ctx(tmp_path, event_type)
    camp = CampPersuasionReport(winner_camp=ctx.winner_camp, prompt_version=ctx.prompt_version)

    candidates = collect_skill_generation_candidates(ctx, camp)

    assert len(candidates) == 1
    assert candidates[0].source_kind == "night_action"
    assert candidates[0].prompt_role_key == "witch"
    assert candidates[0].night_event["event_type"] == event_type
    assert candidates[0].rule.reason == "witch poisoned werewolf"


def test_outcome_scores_do_not_treat_witch_poison_used_as_death(tmp_path: Path) -> None:
    ctx = _witch_poison_ctx(tmp_path, "witch_poison_used")

    scores = build_outcome_scores(ctx)

    assert scores["player_4"]["survival"] == 6
    assert scores["player_9"]["survival"] == 6


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
