"""打分系统单元测试。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.scoring.benefit import build_benefit_scores
from llm_werewolf.evaluation.post_game.scoring.intention import build_intention_scores


def _fixture_events() -> list[dict]:
    return [
        {
            "event_type": "vote_intention_snapshot",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {
                "speaker_id": "player_2",
                "speaker_name": "W",
                "public_speech": "出五号",
                "before": {},
                "after": {},
                "swings": [
                    {
                        "player_id": "player_1",
                        "player_name": "A",
                        "from_target_id": None,
                        "to_target_id": "player_5",
                    },
                ],
                "swing_count": 1,
            },
        },
        {
            "event_type": "vote_cast",
            "round_number": 1,
            "phase": "day_voting",
            "data": {
                "voter_id": "player_1",
                "target_id": "player_5",
            },
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_5", "role": "Guard"},
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_2", "role": "Werewolf"},
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "werewolf", "winner_ids": ["player_2"]},
        },
    ]


def test_intention_scores_swing_to_final_vote(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    from llm_werewolf.evaluation.post_game.vote_swing_analysis import _records_from_events

    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    payload = build_intention_scores(ctx, camp)
    assert payload["schema"] == "intention_scores_v1"
    assert payload["speeches"]
    first = payload["speeches"][0]
    assert "swing_to_final_vote" in first
    assert "persuasion_net" in first


def test_benefit_scores_partial_metrics(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    intention = build_intention_scores(ctx, camp)
    benefit = build_benefit_scores(
        ctx,
        camp,
        intention_by_player=intention.get("by_player"),
    )
    assert benefit["schema"] == "benefit_scores_v2"
    assert benefit["phase"] == "v1_complete"
    assert "survival_at_end" in benefit["implemented_metrics"]
    assert benefit["players"]
