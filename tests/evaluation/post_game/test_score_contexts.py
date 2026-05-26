"""分维度评分上下文隔离。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.scoring.score_contexts import (
    DIM_PERSUASION,
    DIM_WOLF_NIGHT,
    build_score_context_bundles,
    write_score_contexts,
)


def _fixture_events() -> list[dict]:
    return [
        {
            "event_type": "player_speech",
            "round_number": 1,
            "phase": "day_discussion",
            "visible_to": None,
            "data": {"player_id": "player_1", "speech": "白天公开发言"},
        },
        {
            "event_type": "player_discussion",
            "round_number": 1,
            "phase": "night",
            "visible_to": ["player_2", "player_3"],
            "data": {"player_id": "player_2", "speech": "狼队夜间商量刀谁"},
        },
        {
            "event_type": "werewolf_killed",
            "round_number": 1,
            "phase": "night",
            "data": {"target_id": "player_5", "target_name": "玩家5"},
        },
        {
            "event_type": "seer_checked",
            "round_number": 1,
            "phase": "night",
            "visible_to": ["player_1"],
            "data": {"player_id": "player_1", "target_id": "player_2", "result": "werewolf"},
        },
        {
            "event_type": "vote_cast",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"voter_id": "player_1", "target_id": "player_2"},
        },
    ]


def test_score_contexts_isolate_dimensions(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(
            json.dumps(r, ensure_ascii=False)
            for r in [
                {
                    "channel": "public",
                    "phase": "day_discussion",
                    "round_number": 1,
                    "speaker_id": "player_1",
                    "public_speech": "投2号",
                    "swings": [],
                },
                {
                    "channel": "wolf_team",
                    "phase": "night",
                    "round_number": 1,
                    "speaker_id": "player_2",
                    "public_speech": "今晚刀5号",
                    "swings": [],
                },
            ]
        ),
        encoding="utf-8",
    )

    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry

    ctx = load_run_context(tmp_path)
    ctx.roster = {
        "player_1": PlayerRosterEntry("player_1", "玩家1", "Seer", "villager"),
        "player_2": PlayerRosterEntry("player_2", "玩家2", "Werewolf", "werewolf"),
        "player_3": PlayerRosterEntry("player_3", "玩家3", "Werewolf", "werewolf"),
        "player_5": PlayerRosterEntry("player_5", "玩家5", "Villager", "villager"),
    }
    bundles = build_score_context_bundles(ctx)

    pub = bundles[DIM_PERSUASION]
    assert all(str(r.get("channel")) == "public" for r in pub.vote_intention_records)
    assert not any(e.get("event_type") == "seer_checked" for e in pub.events)

    wolf = bundles[DIM_WOLF_NIGHT]
    assert wolf.vote_intention_records
    assert wolf.vote_intention_records[0]["channel"] == "wolf_team"
    assert any(e.get("event_type") == "werewolf_killed" for e in wolf.events)
    assert not any(e.get("event_type") == "player_speech" for e in wolf.events)

    manifest = write_score_contexts(ctx)
    assert (tmp_path / "views" / "score_contexts" / "persuasion.md").is_file()
    assert manifest["policy"] == "each_dimension_isolated_no_global_log_for_scoring"
