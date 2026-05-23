"""投票摇摆说服分析。"""

import json

from llm_werewolf.evaluation.vote_swing_analysis import (
    analyze_speech_records,
    format_markdown_report,
    load_speech_records,
    write_persuasion_artifacts,
)


def _sample_record() -> dict:
    return {
        "round_number": 1,
        "phase": "day_discussion",
        "channel": "public",
        "speaker_id": "player_3",
        "speaker_name": "C",
        "public_speech": "我觉得二号很可疑",
        "before": {
            "player_1": {
                "player_id": "player_1",
                "player_name": "A",
                "seat": 2,
                "target_id": "player_2",
                "target_name": "B",
            },
            "player_2": {
                "player_id": "player_2",
                "player_name": "B",
                "seat": 2,
                "target_id": "player_2",
                "target_name": "B",
            },
        },
        "after": {
            "player_1": {
                "player_id": "player_1",
                "player_name": "A",
                "seat": 3,
                "target_id": "player_3",
                "target_name": "C",
            },
            "player_2": {
                "player_id": "player_2",
                "player_name": "B",
                "seat": 2,
                "target_id": "player_2",
                "target_name": "B",
            },
        },
        "swings": [
            {
                "player_id": "player_1",
                "player_name": "A",
                "from_seat": 2,
                "to_seat": 3,
                "from_target_name": "B",
                "to_target_name": "C",
            }
        ],
        "swing_count": 1,
    }


def test_analyze_speech_records():
    report = analyze_speech_records([_sample_record()])
    assert report.total_speeches == 1
    assert report.total_swings == 1
    stats = report.player_stats["player_3"]
    assert stats.total_swings_caused == 1
    assert stats.total_influence_score == 10


def test_write_persuasion_artifacts(tmp_path):
    path = tmp_path / "vote_intentions.jsonl"
    path.write_text(json.dumps(_sample_record(), ensure_ascii=False) + "\n", encoding="utf-8")
    out = write_persuasion_artifacts(tmp_path)
    assert (out / "vote_swing_report.md").is_file()
    assert (out / "vote_swing_summary.json").is_file()
    loaded = load_speech_records(tmp_path)
    assert len(loaded) == 1
    md = format_markdown_report(analyze_speech_records(loaded))
    assert "C" in md
    assert "Influence" in md or "influence" in md.lower()
