"""MVP 量化。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events
from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry, load_run_context
from llm_werewolf.evaluation.post_game.scoring.mvp import _weights_for_role, build_mvp_scores


def test_mvp_can_be_losing_camp(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "vote_intention_snapshot",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {
                "channel": "public",
                "speaker_id": "player_2",
                "speaker_name": "狼人",
                "public_speech": "强烈建议出5号",
                "before": {},
                "after": {
                    "player_1": {
                        "player_id": "player_1",
                        "to_target_id": "player_5",
                    },
                },
                "swings": [
                    {
                        "player_id": "player_1",
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
            "data": {"voter_id": "player_2", "target_id": "player_5"},
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_5", "role": "Villager"},
        },
        {
            "event_type": "game_ended",
            "round_number": 2,
            "phase": "ended",
            "data": {"winner_camp": "villager", "winner_ids": ["player_1"]},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )

    ctx = load_run_context(tmp_path)
    ctx.roster["player_2"] = PlayerRosterEntry(
        player_id="player_2",
        player_name="狼人",
        role_name="Werewolf",
        camp="werewolf",
    )
    ctx.roster["player_1"] = PlayerRosterEntry(
        player_id="player_1",
        player_name="好人",
        role_name="Villager",
        camp="villager",
    )
    ctx.roster["player_5"] = PlayerRosterEntry(
        player_id="player_5",
        player_name="五号",
        role_name="Villager",
        camp="villager",
    )

    camp = build_camp_persuasion_report(ctx)
    payload = build_mvp_scores(ctx, camp)

    assert payload["schema"] == "mvp_scores_v2"
    assert payload["mvp"] is not None
    assert payload["dimension_context_paths"]
    assert payload["selection_policy"]["overall"] == "highest_mvp_total_any_camp"


def test_weights_renormalized_without_vote_intentions() -> None:
    table = {
        "default": {
            "persuasion": 0.4,
            "strategy": 0.3,
            "outcome": 0.2,
            "wolf_night": 0.1,
        },
    }
    w = _weights_for_role(table, "default", has_vote_intentions=False)
    assert "persuasion" not in w
    assert abs(sum(w.values()) - 1.0) < 1e-6


def test_data_quality_low_without_intentions(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "villager", "winner_ids": ["player_1"]},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    payload = build_mvp_scores(ctx, camp, intention_payload=None)
    assert payload["data_quality"]["confidence"] == "low"
    assert payload["data_quality"]["has_vote_intentions"] is False
