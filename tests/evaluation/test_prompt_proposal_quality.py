"""Prompt 提案质量门控回归。"""

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.evaluation.post_game.run_context import RunContext, PlayerRosterEntry
from llm_werewolf.evaluation.post_game.camp_persuasion import (
    CampAlignedSwing,
    _matched_elimination_for_speaker,
    build_camp_persuasion_report,
)
from llm_werewolf.evaluation.post_game.prompt_proposal import (
    _sanitize_excerpt_for_role,
    _truncate_at_sentence,
    build_prompt_proposals,
)
from llm_werewolf.evaluation.core.vote_swing_analysis import analyze_speech_records


def test_matched_elimination_false_when_villager_mis_eliminated() -> None:
    swings = [
        CampAlignedSwing(
            player_id="player_4",
            player_name="4",
            from_target_id="player_7",
            to_target_id="player_11",
            from_target_camp=Camp.VILLAGER.value,
            to_target_camp=Camp.VILLAGER.value,
            camp_aligned=False,
        )
    ]
    matched = _matched_elimination_for_speaker(
        speaker_camp=Camp.VILLAGER.value,
        elim_target="player_11",
        elim_target_camp=Camp.VILLAGER.value,
        camp_swings=swings,
        drive_count=1,
    )
    assert not matched


def test_matched_elimination_false_when_speaker_camp_unknown() -> None:
    matched = _matched_elimination_for_speaker(
        speaker_camp=None,
        elim_target="player_11",
        elim_target_camp=Camp.VILLAGER.value,
        camp_swings=[],
        drive_count=1,
    )
    assert not matched


def test_matched_elimination_true_when_wolf_eliminated() -> None:
    matched = _matched_elimination_for_speaker(
        speaker_camp=Camp.VILLAGER.value,
        elim_target="player_6",
        elim_target_camp=Camp.WEREWOLF.value,
        camp_swings=[],
        drive_count=2,
    )
    assert matched


def test_matched_elimination_true_without_swing_when_advocated_target_matches() -> None:
    matched = _matched_elimination_for_speaker(
        speaker_camp=Camp.VILLAGER.value,
        elim_target="player_6",
        elim_target_camp=Camp.WEREWOLF.value,
        camp_swings=[],
        drive_count=0,
        speaker_advocated_target="player_6",
    )
    assert matched


def test_truncate_at_sentence_avoids_half_sentence() -> None:
    text = "现在是平安夜，神职可以适当跳出来给信息，大家今天都不许划水，把上一轮投票的理由说清楚。"
    out = _truncate_at_sentence(text, max_len=60)
    assert out.endswith("。")
    assert "大家今天都。" not in out


def test_sanitize_guard_excerpt_strips_lover_context() -> None:
    raw = (
        "我可以证明7号说的我和2号是情侣是对的，我确实是好人阵营。"
        "另外4号你说你第二轮救了1号，但昨夜1号明明被狼刀死了，你明显是悍跳女巫的狼。"
    )
    out = _sanitize_excerpt_for_role(raw, "guard")
    assert "情侣" not in out
    assert "另外4号" in out


def test_build_prompt_proposals_adds_mis_elimination_bad_case() -> None:
    ctx = RunContext(
        run_dir=".",
        events=[
            {
                "event_type": "player_eliminated",
                "round_number": 3,
                "phase": "day_voting",
                "data": {"player_id": "player_11", "role": "Seer"},
            }
        ],
        roster={
            "player_11": PlayerRosterEntry(
                "player_11", "11", role_name="Seer", camp=Camp.VILLAGER.value
            ),
        },
        winner_camp=Camp.VILLAGER.value,
        prompt_version="latest",
    )
    camp = build_camp_persuasion_report(ctx, analyze_speech_records([]))
    payload = build_prompt_proposals(ctx, camp)
    kinds = {p["kind"] for p in payload["proposals"]}
    assert "bad_case_rule" in kinds
    assert any(p["proposal_id"].startswith("bad_case_mis_elim_") for p in payload["proposals"])
