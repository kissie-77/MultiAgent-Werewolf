"""打分系统单元测试。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.scoring.mvp import build_mvp_scores
from llm_werewolf.evaluation.scoring.benefit import build_benefit_scores
from llm_werewolf.evaluation.scoring.intention import build_intention_scores


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
    from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events

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
    mvp_payload = build_mvp_scores(ctx, camp, intention_payload=intention)
    benefit = build_benefit_scores(
        ctx,
        camp,
        intention_by_player=intention.get("by_player"),
        mvp_payload=mvp_payload,
    )
    assert benefit["schema"] == "benefit_scores_v2"
    assert benefit["phase"] == "mvp_integrated"
    assert benefit["players"]
    mvp_by_player = {row["player_id"]: row for row in mvp_payload["players"]}
    for row in benefit["players"]:
        pid = row["player_id"]
        assert row["total"] == round(float(mvp_by_player[pid]["mvp_total"]), 1)


def test_benefit_scores_preserves_zero_mvp_total(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    mvp_payload = {
        "schema": "mvp_scores_v2",
        "players": [
            {
                "player_id": pid,
                "mvp_total": 0.0,
                "breakdown_raw": {
                    "persuasion": 0,
                    "strategy": 0,
                    "outcome": 0,
                    "wolf_night": 0,
                },
                "breakdown_norm": {},
                "rank": idx + 1,
            }
            for idx, pid in enumerate(ctx.roster)
        ],
    }
    benefit = build_benefit_scores(ctx, camp, mvp_payload=mvp_payload)
    assert benefit["phase"] == "mvp_integrated"
    assert all(row["total"] == 0.0 for row in benefit["players"])
