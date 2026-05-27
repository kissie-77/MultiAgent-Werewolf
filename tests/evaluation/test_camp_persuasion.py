"""阵营匹配说服分析。"""

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import (
    PlayerRosterEntry,
    RunContext,
    is_camp_aligned_vote_target,
)
from llm_werewolf.evaluation.core.vote_swing_analysis import analyze_speech_records
from llm_werewolf.game_runtime.types.enums import Camp


def test_camp_aligned_target_rules() -> None:
    assert is_camp_aligned_vote_target(Camp.WEREWOLF.value, Camp.VILLAGER.value)
    assert is_camp_aligned_vote_target(Camp.VILLAGER.value, Camp.WEREWOLF.value)
    assert not is_camp_aligned_vote_target(Camp.WEREWOLF.value, Camp.WEREWOLF.value)
    assert not is_camp_aligned_vote_target(Camp.VILLAGER.value, Camp.VILLAGER.value)


def test_build_camp_persuasion_scores_aligned_swings() -> None:
    records = [
        {
            "round_number": 1,
            "phase": "day_discussion",
            "channel": "public",
            "speaker_id": "player_2",
            "speaker_name": "狼",
            "public_speech": "出五号",
            "before": {},
            "after": {},
                "swings": [
                    {
                        "player_id": "player_3",
                        "player_name": "好",
                        "from_target_id": "player_2",
                        "to_target_id": "player_5",
                        "from_target_name": "狼",
                        "to_target_name": "守",
                    },
                ],
            "swing_count": 1,
        },
    ]
    swing_report = analyze_speech_records(records)
    ctx = RunContext(
        run_dir=".",
        roster={
            "player_2": PlayerRosterEntry(
                "player_2", "狼", role_name="Werewolf", camp=Camp.WEREWOLF.value
            ),
            "player_3": PlayerRosterEntry(
                "player_3", "好", role_name="Villager", camp=Camp.VILLAGER.value
            ),
            "player_5": PlayerRosterEntry(
                "player_5", "守", role_name="Guard", camp=Camp.VILLAGER.value
            ),
        },
        winner_camp=Camp.WEREWOLF.value,
        prompt_version="v2",
    )
    report = build_camp_persuasion_report(ctx, swing_report)
    speech = report.speeches[0]
    assert speech.speaker_camp == Camp.WEREWOLF.value
    assert speech.camp_aligned_swings >= 1
    assert speech.camp_aligned_score >= 10
