"""多轮 evolution fixture 集成测试。

验证 version chain / leaderboard / skill diff / 版本摘要的完整流程。
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.evaluation.conftest_evolution import build_evolution_fixtures


def test_fixture_creates_three_runs(tmp_path: Path) -> None:
    """3 轮 fixture 应创建 3 个 run 目录。"""
    run_dirs = build_evolution_fixtures(tmp_path)
    assert len(run_dirs) == 3
    for d in run_dirs:
        assert d.is_dir()


def test_fixture_each_run_has_core_artifacts(tmp_path: Path) -> None:
    """每个 run 应包含核心产物。"""
    run_dirs = build_evolution_fixtures(tmp_path)
    required = [
        "events.jsonl",
        "post_game_manifest.json",
        "summary.json",
        "leaderboard_entry.json",
        "experiment_meta.json",
        "skill_snapshot.json",
        "skill_diff.json",
        "benefit_scores.json",
        "intention_scores.json",
    ]
    for run_dir in run_dirs:
        for fname in required:
            assert (run_dir / fname).is_file(), f"{run_dir.name}: missing {fname}"


def test_fixture_has_skill_md_files(tmp_path: Path) -> None:
    """每个 run 的 skills/ 目录应有 skill MD 文件。"""
    run_dirs = build_evolution_fixtures(tmp_path)
    for run_dir in run_dirs:
        skills_dir = run_dir / "skills"
        assert skills_dir.is_dir()
        md_files = list(skills_dir.glob("*.md"))
        assert len(md_files) >= 3, f"{run_dir.name}: expected >= 3 skill files, got {len(md_files)}"


def test_version_chain_links_correctly(tmp_path: Path) -> None:
    """experiment_meta 应正确链接版本链：v2 -> v1, v3 -> v2。"""
    run_dirs = build_evolution_fixtures(tmp_path)

    meta1 = json.loads((run_dirs[0] / "experiment_meta.json").read_text(encoding="utf-8"))
    meta2 = json.loads((run_dirs[1] / "experiment_meta.json").read_text(encoding="utf-8"))
    meta3 = json.loads((run_dirs[2] / "experiment_meta.json").read_text(encoding="utf-8"))

    assert meta1["previous_run_dir"] is None
    assert meta2["previous_run_dir"] == "v1-baseline"
    assert meta3["previous_run_dir"] == "v2-skill-evolved"


def test_skill_diff_shows_changes(tmp_path: Path) -> None:
    """v2 和 v3 的 skill_diff 应包含新增或变更。"""
    run_dirs = build_evolution_fixtures(tmp_path)

    # v1: 无变更
    diff1 = json.loads((run_dirs[0] / "skill_diff.json").read_text(encoding="utf-8"))
    assert diff1["added"] == []
    assert diff1["changed"] == []

    # v2: 新增 guard skill
    diff2 = json.loads((run_dirs[1] / "skill_diff.json").read_text(encoding="utf-8"))
    assert len(diff2["added"]) == 1
    assert diff2["added"][0]["skill_id"] == "guard_night_r1_protect"

    # v3: wolf skill 权重变更
    diff3 = json.loads((run_dirs[2] / "skill_diff.json").read_text(encoding="utf-8"))
    assert len(diff3["changed"]) == 1
    assert diff3["changed"][0]["skill_id"] == "wolf_r1_night_knife_align"


def test_win_rate_increases_across_versions(tmp_path: Path) -> None:
    """胜率应随版本递增：0.6 -> 0.7 -> 0.8。"""
    run_dirs = build_evolution_fixtures(tmp_path)
    win_rates = []
    for run_dir in run_dirs:
        entry = json.loads((run_dir / "leaderboard_entry.json").read_text(encoding="utf-8"))
        win_rates.append(entry["win_rate"])
    assert win_rates == [0.6, 0.7, 0.8]


def test_leaderboard_entries_are_complete(tmp_path: Path) -> None:
    """每个 leaderboard_entry 应包含所有必要字段。"""
    run_dirs = build_evolution_fixtures(tmp_path)
    required_fields = [
        "schema", "version_id", "model", "prompt_version", "skill_version",
        "games", "win_rate", "avg_mvp_score", "avg_benefit_score",
    ]
    for run_dir in run_dirs:
        entry = json.loads((run_dir / "leaderboard_entry.json").read_text(encoding="utf-8"))
        for field in required_fields:
            assert field in entry, f"{run_dir.name}: missing {field}"


def test_leaderboard_aggregation_works(tmp_path: Path) -> None:
    """leaderboard 聚合应能正确收集所有 entry。"""
    from llm_werewolf.evaluation.leaderboard.aggregator import collect_entries

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)
    entries = collect_entries(runs_dir)
    assert len(entries) == 3
    # 按 win_rate 降序排列
    rates = [e["win_rate"] for e in entries]
    assert rates == sorted(rates, reverse=True)


def test_skill_snapshot_weight_evolution(tmp_path: Path) -> None:
    """skill 权重应随版本递增。"""
    run_dirs = build_evolution_fixtures(tmp_path)
    wolf_weights = []
    for run_dir in run_dirs:
        snapshot = json.loads((run_dir / "skill_snapshot.json").read_text(encoding="utf-8"))
        wolf_skill = snapshot["skills"]["wolf_r1_night_knife_align"]
        wolf_weights.append(wolf_skill["weight"])
    assert wolf_weights[0] < wolf_weights[1] < wolf_weights[2]


def test_enhanced_summary_generation(tmp_path: Path) -> None:
    """增强版产物（active skill 清单、版本摘要、evolution overview）应能正常生成。"""
    from llm_werewolf.evaluation.leaderboard.summary_enhanced import (
        write_active_skill_summary,
        write_evolution_overview,
        write_version_summaries,
    )

    # 在隔离目录中构建 fixture，避免干扰 artifacts/runs/ 的真实数据
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    build_evolution_fixtures(runs_dir)
    output_dir = tmp_path / "leaderboards"

    p1 = write_active_skill_summary(runs_dir, output_dir)
    assert p1.is_file()

    p2 = write_version_summaries(runs_dir, output_dir)
    assert p2.is_dir()
    assert len(list(p2.glob("*.md"))) == 3

    p3 = write_evolution_overview(runs_dir, output_dir)
    assert p3.is_file()
    content = p3.read_text(encoding="utf-8")
    assert "v1-baseline" in content
    assert "v3-skill-matured" in content
