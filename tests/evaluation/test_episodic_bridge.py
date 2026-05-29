"""PostGame 与 EpisodicMemory 对接测试。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.coach.coach import Coach
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.episodic_bridge import (
    episodic_memory_for_run,
    write_episodic_artifacts,
    export_player_episode_reports,
)


def _fixture_events() -> list[dict]:
    return [
        {
            "event_type": "vote_cast",
            "round_number": 1,
            "phase": "day_voting",
            "message": "A votes B",
            "data": {"voter_id": "player_1", "target_id": "player_2"},
            "visible_to": None,
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "message": "B eliminated",
            "data": {"player_id": "player_2", "role": "Werewolf"},
            "visible_to": None,
        },
        {
            "event_type": "role_acting",
            "round_number": 1,
            "phase": "night",
            "message": "Seer acts",
            "data": {"player_id": "player_1", "role": "Seer", "player_name": "A"},
            "visible_to": ["player_1"],
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "message": "ended",
            "data": {"winner_camp": "villager", "winner_ids": ["player_1"]},
            "visible_to": None,
        },
    ]


def test_episodic_memory_from_run_context(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    episodic = episodic_memory_for_run(ctx)
    assert len(episodic.get_all_events()) >= 3

    reports = export_player_episode_reports(ctx)
    assert reports["schema"] == "episodic_reports_v1"
    assert "player_1" in reports["by_player"]


def test_write_episodic_artifacts_and_coach_enrich(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    path = write_episodic_artifacts(ctx)
    assert path.is_file()

    skills_payload = {
        "skill_count": 1,
        "skills": [
            {
                "skill_id": "test_skill",
                "source_player_id": "player_1",
                "status": "draft",
                "evidence": {"round_number": 1},
            }
        ],
    }
    coach = Coach()
    result = coach.enrich_skills_with_episodes(ctx, skills_payload["skills"])
    assert result.enriched_skill_count >= 0
    from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report

    coach.write_coach_artifacts(
        ctx, build_camp_persuasion_report(ctx), skills_payload, coach_result=result
    )
    assert (tmp_path / "coach_summary.json").is_file()
