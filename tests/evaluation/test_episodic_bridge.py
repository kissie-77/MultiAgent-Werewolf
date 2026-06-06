"""PostGame 与 EpisodicMemory 对接测试。"""

import json
from pathlib import Path

from llm_werewolf.agent_team.memory.semantic_memory import InMemoryBackend, SemanticMemory
from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
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
    assert (tmp_path / "skill_snapshot.json").is_file()
    assert (tmp_path / "skill_diff.json").is_file()


def test_coach_extracts_runtime_semantic_candidates_from_episode_report(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    reports = export_player_episode_reports(ctx)
    report = reports["by_player"]["player_1"]
    coach = Coach()
    semantic = SemanticMemory(backend=InMemoryBackend())

    candidates = coach.extract_semantic_candidates(
        report,
        won=True,
        semantic=semantic,
        top_k=3,
    )

    assert candidates
    assert any("胜利经验" in candidate or "关键局势复盘" in candidate for candidate in candidates)


def test_coach_writes_skill_snapshot_and_diff_with_previous_version(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    previous_run_dir = tmp_path / "previous_run"
    previous_run_dir.mkdir(parents=True, exist_ok=True)
    previous_snapshot = {
        "schema": "skill_snapshot_v1",
        "skill_count": 1,
        "skills": [
            {
                "skill_id": "test_skill",
                "prompt_role_key": "villager",
                "source_player_id": "player_1",
                "status": "draft",
                "weight": 1.0,
                "win_count": 0,
                "use_count": 0,
                "description": "第1轮白天，使用该 skill",
            }
        ],
    }
    (previous_run_dir / "skill_snapshot.json").write_text(
        json.dumps(previous_snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "experiment_meta.json").write_text(
        json.dumps(
            {
                "schema": "experiment_meta_v1",
                "previous_run_dir": str(previous_run_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)

    skills_payload = {
        "skill_count": 2,
        "skills": [
            {
                "skill_id": "test_skill",
                "prompt_role_key": "villager",
                "source_player_id": "player_1",
                "status": "active",
                "weight": 1.2,
                "win_count": 1,
                "use_count": 2,
                "skill_card": {"when_to_use": "第1轮白天，使用该 skill"},
                "evidence": {"round_number": 1},
            },
            {
                "skill_id": "new_skill",
                "prompt_role_key": "wolf",
                "source_player_id": "player_2",
                "status": "draft",
                "weight": 1.0,
                "win_count": 0,
                "use_count": 0,
                "skill_card": {"when_to_use": "第2轮夜晚，使用该 skill"},
                "evidence": {"round_number": 1},
            },
        ],
    }
    coach = Coach()
    coach.write_coach_artifacts(
        ctx,
        build_camp_persuasion_report(ctx),
        skills_payload,
    )

    snapshot = json.loads((tmp_path / "skill_snapshot.json").read_text(encoding="utf-8"))
    diff = json.loads((tmp_path / "skill_diff.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "coach_summary.json").read_text(encoding="utf-8"))

    assert snapshot["schema"] == "skill_snapshot_v1"
    assert snapshot["skill_count"] == 2
    assert diff["schema"] == "skill_diff_v1"
    assert diff["has_previous_version"] is True
    assert diff["added_count"] == 1
    assert diff["changed_count"] == 1
    assert diff["added"][0]["skill_id"] == "new_skill"
    assert diff["changed"][0]["skill_id"] == "test_skill"
    assert summary["skill_snapshot"]["skill_count"] == 2
    assert summary["skill_diff"]["added_count"] == 1
