"""PostGame 流水线与 Prompt 提案 JSON。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.prompt_proposal import build_prompt_proposals
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.pipeline import run_post_game_pipeline_sync
from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events


def test_prompt_proposals_json_only_policy(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "vote_intention_snapshot",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {
                "round_number": 1,
                "phase": "day_discussion",
                "channel": "public",
                "speaker_id": "player_2",
                "speaker_name": "B",
                "public_speech": "投五号",
                "before": {
                    "player_1": {
                        "player_id": "player_1",
                        "player_name": "A",
                        "seat": 0,
                        "target_id": None,
                        "target_name": None,
                    },
                },
                "after": {
                    "player_1": {
                        "player_id": "player_1",
                        "player_name": "A",
                        "seat": 5,
                        "target_id": "player_5",
                        "target_name": "E",
                    },
                },
                "swings": [
                    {
                        "player_id": "player_1",
                        "player_name": "A",
                        "from_seat": 0,
                        "to_seat": 5,
                        "from_target_id": None,
                        "to_target_id": "player_5",
                        "from_target_name": None,
                        "to_target_name": "E",
                    },
                ],
                "swing_count": 1,
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
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )

    result = run_post_game_pipeline_sync(tmp_path, skip_llm=True)
    assert result.error is None
    assert result.ok
    assert (tmp_path / "episodic_reports.json").is_file()
    assert (tmp_path / "coach_summary.json").is_file()
    assert (tmp_path / "prompt_proposals.json").is_file()

    payload = json.loads((tmp_path / "prompt_proposals.json").read_text(encoding="utf-8"))
    assert payload["apply_policy"] == "json_only_no_runtime_replace"
    assert payload["prompt_version_base"] == "v2"
    assert payload["schema"] == "prompt_proposals_v2"
    assert payload["proposal_count"] >= 1
    assert "target_variable" in payload["proposals"][0]

    assert (tmp_path / "role_skills.json").is_file()
    assert (tmp_path / "intention_scores.json").is_file()
    assert (tmp_path / "benefit_scores.json").is_file()
    assert (tmp_path / "views_manifest.json").is_file()
    skills_payload = json.loads((tmp_path / "role_skills.json").read_text(encoding="utf-8"))
    assert skills_payload["schema"] == "role_skills_v1"

    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    proposals = build_prompt_proposals(ctx, camp)
    assert proposals["proposals"][0]["kind"] in {"positive_persuasion", "bad_case_rule"}
