import json
from pathlib import Path

from llm_werewolf.evaluation.evolution.runner import run_evolution_cycle
from tests.evaluation.conftest_evolution import build_evolution_fixtures


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
    assert "version_diff_summaries" in payload
    assert len(payload["round_skill_summaries"]) == 2
    assert len(payload["version_diff_summaries"]) == 2
    assert payload["round_skill_summaries"][0]["version_id"] == "v1_initial"
    assert "active_skill_count" in payload["round_skill_summaries"][0]
    assert "added_skill_ids" in payload["round_skill_summaries"][0]
    assert "removed_skill_ids" in payload["round_skill_summaries"][0]
    assert payload["version_diff_summaries"][0]["version_id"] == "v1_initial"
    assert payload["version_diff_summaries"][0]["previous_version_id"] is None
    assert "role_count_changes" in payload["version_diff_summaries"][0]
    assert "net_active_skill_delta" in payload["version_diff_summaries"][0]
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


# ── mimo1 产物测试 ──────────────────────────────────────────────────


def test_active_skills_json_generated(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import write_active_skill_summary

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)
    out = tmp_path / "out"

    write_active_skill_summary(runs_dir, out)

    json_path = out / "active_skills.json"
    assert json_path.is_file()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "active_skills_v1"
    assert isinstance(payload["skills"], list)
    assert payload["total"] == len(payload["skills"])


def test_active_skills_md_generated(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import write_active_skill_summary

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)
    out = tmp_path / "out"

    write_active_skill_summary(runs_dir, out)

    md_path = out / "active_skills.md"
    assert md_path.is_file()
    content = md_path.read_text(encoding="utf-8")
    assert "Active Skill" in content


def test_version_manifest_generated_per_run(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import write_all_version_manifests

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)

    paths = write_all_version_manifests(runs_dir)
    assert len(paths) == 3
    for p in paths:
        assert p.is_file()
        assert p.name == "version_manifest.json"


def test_version_manifest_has_required_fields(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import write_all_version_manifests

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)

    paths = write_all_version_manifests(runs_dir)
    payload = json.loads(paths[0].read_text(encoding="utf-8"))

    required = [
        "schema", "version_id", "prompt_version", "skill_version",
        "model", "active_skill_count", "scenario", "games", "win_rate",
    ]
    for field in required:
        assert field in payload, f"missing field: {field}"
    assert payload["schema"] == "version_manifest_v1"


def test_version_manifest_links_previous(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import write_all_version_manifests

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)

    paths = write_all_version_manifests(runs_dir)
    manifests = [json.loads(p.read_text(encoding="utf-8")) for p in paths]

    assert manifests[0]["previous_run_dir"] is None
    assert manifests[1]["previous_run_dir"] == "v1-baseline"
    assert manifests[2]["previous_run_dir"] == "v2-skill-evolved"


def test_evolution_summary_generated(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import write_evolution_summary

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)
    out = tmp_path / "out"

    p = write_evolution_summary(runs_dir, out)
    assert p.is_file()
    content = p.read_text(encoding="utf-8")
    assert "v1-baseline" in content
    assert "初始版 vs 终局版" in content


def test_evolution_trend_win_rates_ascending(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import write_evolution_trend

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)
    out = tmp_path / "out"

    json_path, _ = write_evolution_trend(runs_dir, out)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rates = [v["win_rate"] for v in payload["versions"]]
    assert rates == [0.6, 0.7, 0.8]


def test_backfill_generates_missing_files(tmp_path: Path) -> None:
    from scripts.backfill_run_artifacts import backfill_run

    run_dir = tmp_path / "20260526-test"
    run_dir.mkdir()
    (run_dir / "post_game_manifest.json").write_text(
        json.dumps({"context": {"run_dir": "x", "prompt_version": "v2", "winner_camp": "werewolf", "roster": {}}}),
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "GAME_STARTED", "round_number": 0, "phase": "setup", "data": {}, "visible_to": None}),
        encoding="utf-8",
    )
    (run_dir / "benefit_scores.json").write_text("[]", encoding="utf-8")
    (run_dir / "intention_scores.json").write_text("[]", encoding="utf-8")
    (run_dir / "role_skills.json").write_text("[]", encoding="utf-8")
    (run_dir / "camp_persuasion_summary.json").write_text("{}", encoding="utf-8")

    result = backfill_run(run_dir)
    assert (run_dir / "leaderboard_entry.json").is_file()
    assert (run_dir / "experiment_meta.json").is_file()
    assert result["status"] in ("usable", "partial")


def test_backfill_dry_run_does_not_write(tmp_path: Path) -> None:
    from scripts.backfill_run_artifacts import backfill_run

    run_dir = tmp_path / "20260526-test"
    run_dir.mkdir()
    (run_dir / "post_game_manifest.json").write_text(
        json.dumps({"context": {"run_dir": "x", "prompt_version": "v2", "winner_camp": "werewolf", "roster": {}}}),
        encoding="utf-8",
    )

    backfill_run(run_dir, dry_run=True)
    assert not (run_dir / "leaderboard_entry.json").is_file()
    assert not (run_dir / "experiment_meta.json").is_file()


def test_rollback_list_finds_versions(tmp_path: Path) -> None:
    from scripts.rollback_helper import list_versions

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)

    versions = list_versions(runs_dir)
    assert len(versions) == 3
    assert versions[0]["version_id"] == "v1-baseline"


def test_rollback_show_returns_detail(tmp_path: Path) -> None:
    from scripts.rollback_helper import show_version

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)

    result = show_version(runs_dir, "v1-baseline")
    assert result is not None
    assert result["version_id"] == "v1-baseline"
    assert "leaderboard_entry" in result


def test_rollback_candidate_compares_versions(tmp_path: Path) -> None:
    from scripts.rollback_helper import generate_rollback_candidate

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)

    candidate = generate_rollback_candidate(runs_dir, "v1-baseline")
    assert candidate is not None
    assert candidate["target_version"] == "v1-baseline"
    assert candidate["current_version"] == "v3-skill-matured"
    assert "summary" in candidate
