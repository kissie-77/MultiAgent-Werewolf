import json
from pathlib import Path

from llm_werewolf.evaluation.evolution.runner import run_evolution_cycle


def test_run_evolution_cycle_writes_rounds_and_reports(tmp_path: Path) -> None:
    summary_path = run_evolution_cycle(
        output_root=tmp_path,
        scenario="smoke_6p_basic",
        rounds=2,
        games_per_round=1,
        timeout_seconds=20,
        seed=3,
        model="demo",
        prompt_version="prompt_v1",
        initial_skill_version="baseline",
        notes=["evolution-test"],
    )

    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["schema"] == "evolution_cycle_v1"
    assert payload["round_count"] == 2
    assert (tmp_path / "v1_initial" / "leaderboard_entry.json").is_file()
    assert (tmp_path / "v2_evolved" / "leaderboard_entry.json").is_file()
    assert (tmp_path / "v1_initial" / "version_manifest.json").is_file()
    assert (tmp_path / "v2_evolved" / "version_manifest.json").is_file()
    assert (tmp_path / "leaderboards" / "leaderboard.json").is_file()
    assert (tmp_path / "ab_reports").is_dir()
    assert payload["ab_report_path"] is not None
    assert "round_skill_summaries" in payload
    assert len(payload["round_skill_summaries"]) == 2
    assert payload["round_skill_summaries"][0]["version_id"] == "v1_initial"
    assert "active_skill_count" in payload["round_skill_summaries"][0]
    assert "added_skill_ids" in payload["round_skill_summaries"][0]
    assert "removed_skill_ids" in payload["round_skill_summaries"][0]
    manifest_payload = json.loads((tmp_path / "v1_initial" / "version_manifest.json").read_text(encoding="utf-8"))
    assert manifest_payload["schema"] == "agent_version_manifest_v1"
    assert manifest_payload["prompt_version"] == "prompt_v1"
    assert "active_skills" in manifest_payload
    assert "memory_runtime_params" in manifest_payload
    assert "model_config" in manifest_payload


def test_restore_active_skills_from_manifest_rebuilds_runtime_library(
    tmp_path: Path, monkeypatch
) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader
    from llm_werewolf.evaluation.evolution.version_manifest import restore_active_skills_from_manifest

    skill_root = tmp_path / "runtime_skills"
    source_root = tmp_path / "source_skills"
    wolf_source_dir = source_root / "wolf"
    wolf_source_dir.mkdir(parents=True, exist_ok=True)
    source_skill = wolf_source_dir / "wolf_demo.md"
    source_skill.write_text(
        "---\nskill_id: wolf_demo\nprompt_role_key: wolf\nstatus: active\nweight: 1.20\n---\n\n# Demo\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: skill_root)
    skill_loader.list_role_skill_files.cache_clear()

    manifest_path = tmp_path / "version_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "agent_version_manifest_v1",
                "version_id": "v1_initial",
                "prompt_version": "prompt_v1",
                "active_skills": {
                    "wolf": [
                        {
                            "skill_id": "wolf_demo",
                            "status": "active",
                            "weight": 1.2,
                            "description": "第1轮使用该 skill",
                            "path": str(source_skill),
                        }
                    ]
                },
                "memory_runtime_params": {},
                "model_config": {"model": "demo", "reasoning_effort": None},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    restore_active_skills_from_manifest(manifest_path)

    restored = skill_root / "wolf" / "wolf_demo.md"
    assert restored.is_file()
    assert "wolf_demo" in restored.read_text(encoding="utf-8")


def test_restore_active_skills_from_manifest_replaces_existing_runtime_skills(
    tmp_path: Path, monkeypatch
) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader
    from llm_werewolf.evaluation.evolution.version_manifest import restore_active_skills_from_manifest

    skill_root = tmp_path / "runtime_skills"
    stale_role_dir = skill_root / "wolf"
    stale_role_dir.mkdir(parents=True, exist_ok=True)
    (stale_role_dir / "stale.md").write_text("# stale\n", encoding="utf-8")

    source_root = tmp_path / "source_skills"
    wolf_source_dir = source_root / "wolf"
    wolf_source_dir.mkdir(parents=True, exist_ok=True)
    source_skill = wolf_source_dir / "wolf_demo.md"
    source_skill.write_text(
        "---\nskill_id: wolf_demo\nprompt_role_key: wolf\nstatus: active\nweight: 1.20\n---\n\n# Demo\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: skill_root)
    skill_loader.list_role_skill_files.cache_clear()

    manifest_path = tmp_path / "version_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "agent_version_manifest_v1",
                "version_id": "v1_initial",
                "prompt_version": "prompt_v1",
                "active_skills": {
                    "wolf": [
                        {
                            "skill_id": "wolf_demo",
                            "status": "active",
                            "weight": 1.2,
                            "description": "第1轮的情况下，使用该 skill",
                            "path": str(source_skill),
                        }
                    ]
                },
                "memory_runtime_params": {},
                "model_config": {"model": "demo", "reasoning_effort": None},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    restore_active_skills_from_manifest(manifest_path)

    assert not (skill_root / "wolf" / "stale.md").exists()
    restored = skill_root / "wolf" / "wolf_demo.md"
    assert restored.is_file()
    assert "wolf_demo" in restored.read_text(encoding="utf-8")
