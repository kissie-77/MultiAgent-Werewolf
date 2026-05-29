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


def test_score_contexts_isolate_channels(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "vote_intention_snapshot",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {
                "channel": "public",
                "speaker_id": "player_1",
                "public_speech": "白天发言",
            },
        },
        {
            "event_type": "player_discussion",
            "round_number": 1,
            "phase": "night",
            "visible_to": ["player_2", "player_3"],
            "data": {
                "channel": "wolf_team",
                "speaker_id": "player_2",
                "public_speech": "今晚刀5号",
            },
        },
        {
            "event_type": "werewolf_killed",
            "round_number": 1,
            "phase": "night",
            "data": {"target_id": "player_5"},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(
            json.dumps(row, ensure_ascii=False)
            for row in [
                {
                    "channel": "public",
                    "round_number": 1,
                    "phase": "day_discussion",
                    "speaker_id": "player_1",
                    "public_speech": "白天发言",
                },
                {
                    "channel": "wolf_team",
                    "round_number": 1,
                    "speaker_id": "player_2",
                    "public_speech": "今晚刀5号",
                },
            ]
        ),
        encoding="utf-8",
    )

    ctx = load_run_context(tmp_path)
    bundles = build_score_context_bundles(ctx)
    assert bundles[DIM_PERSUASION].vote_intention_records
    assert bundles[DIM_WOLF_NIGHT].vote_intention_records
    assert all(
        e.get("event_type") != "player_discussion"
        for e in bundles[DIM_PERSUASION].events
    )

    manifest = write_score_contexts(ctx)
    assert (tmp_path / "views" / "score_contexts" / "manifest.json").is_file()
    assert manifest["paths"][DIM_PERSUASION]
