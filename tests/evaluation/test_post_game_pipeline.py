"""PostGame 流水线与 Prompt 提案 JSON。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.pipeline import run_post_game_pipeline_sync
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events
from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.prompt_proposal import build_prompt_proposals


def test_prompt_proposals_auto_evolve_policy(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "role_acting",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_2", "role": "Werewolf", "player_name": "B"},
        },
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
                    }
                },
                "after": {
                    "player_1": {
                        "player_id": "player_1",
                        "player_name": "A",
                        "seat": 5,
                        "target_id": "player_5",
                        "target_name": "E",
                    }
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
                    }
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
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "werewolf", "winner_ids": ["player_2"]},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8"
    )

    result = run_post_game_pipeline_sync(tmp_path, skip_llm=True)
    assert result.error is None
    assert result.ok
    assert (tmp_path / "episodic_reports.json").is_file()
    assert (tmp_path / "coach_summary.json").is_file()
    assert (tmp_path / "skill_snapshot.json").is_file()
    assert (tmp_path / "skill_diff.json").is_file()
    assert (tmp_path / "prompt_proposals.json").is_file()
    assert (tmp_path / "counterfactual_report.json").is_file()
    assert (tmp_path / "counterfactual_report.md").is_file()

    payload = json.loads((tmp_path / "prompt_proposals.json").read_text(encoding="utf-8"))
    assert payload["apply_policy"] == "auto_evolve_next_prompt_version"
    assert payload["prompt_version_base"] == "v2"
    assert payload["schema"] == "prompt_proposals_v3"
    assert payload["proposal_count"] >= 1
    assert "target_variable" in payload["proposals"][0]

    assert (tmp_path / "role_skills.json").is_file()
    assert (tmp_path / "intention_scores.json").is_file()
    assert (tmp_path / "benefit_scores.json").is_file()
    assert (tmp_path / "mvp_scores.json").is_file()
    assert (tmp_path / "game_quality_report.md").is_file()
    assert (tmp_path / "post_game_steps.json").is_file()
    assert (tmp_path / "views_manifest.json").is_file()
    skills_payload = json.loads((tmp_path / "role_skills.json").read_text(encoding="utf-8"))
    assert skills_payload["schema"] == "role_skills_v1"
    coach_summary = json.loads((tmp_path / "coach_summary.json").read_text(encoding="utf-8"))
    assert coach_summary["skill_snapshot"]["schema"] == "skill_snapshot_v1"
    assert coach_summary["skill_diff"]["schema"] == "skill_diff_v1"

    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    mvp_payload = json.loads((tmp_path / "mvp_scores.json").read_text(encoding="utf-8"))
    proposals = build_prompt_proposals(ctx, camp, mvp_payload=mvp_payload)
    kinds = {p["kind"] for p in proposals["proposals"]}
    assert kinds & {
        "positive_persuasion",
        "bad_case_rule",
        "mvp_golden_quote",
        "mvp_strategy_highlight",
    }


def test_bad_case_proposal_uses_role_stage_target_when_player_is_known(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "player_speech",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {"player_id": "player_2", "speech": "5"},
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
    (tmp_path / "vote_intentions.jsonl").write_text("", encoding="utf-8")

    result = run_post_game_pipeline_sync(tmp_path, skip_llm=True)
    assert result.ok

    payload = json.loads((tmp_path / "prompt_proposals.json").read_text(encoding="utf-8"))
    bad_cases = [p for p in payload["proposals"] if p["kind"] == "bad_case_rule"]
    assert bad_cases
    assert any(
        p["target_variable"].startswith("v2.role.")
        and p["suggested_patch"]["target_field"].startswith("phase_strategies.")
        for p in bad_cases
    )
