"""MVP 量化。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.scoring.mvp import build_mvp_scores
from llm_werewolf.evaluation.post_game.vote_swing_analysis import _records_from_events


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

    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry

    ctx = load_run_context(tmp_path)
    ctx.roster = {
        "player_1": PlayerRosterEntry(
            player_id="player_1",
            player_name="好人",
            role_name="Villager",
            camp="villager",
        ),
        "player_2": PlayerRosterEntry(
            player_id="player_2",
            player_name="狼人",
            role_name="Werewolf",
            camp="werewolf",
        ),
        "player_5": PlayerRosterEntry(
            player_id="player_5",
            player_name="五号",
            role_name="Villager",
            camp="villager",
        ),
    }
    ctx.winner_camp = "villager"

    camp = build_camp_persuasion_report(ctx)
    payload = build_mvp_scores(ctx, camp)

    assert payload["schema"] == "mvp_scores_v2"
    assert payload["mvp"] is not None
    assert payload["dimension_context_paths"]
    assert payload["selection_policy"]["overall"] == "highest_mvp_total_any_camp"
