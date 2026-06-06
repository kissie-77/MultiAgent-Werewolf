"""Leaderboard CLI entrypoint tests."""

from __future__ import annotations

import json
from pathlib import Path

from llm_werewolf.evaluation.leaderboard.cli import main


def _write_run_fixture(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "total_games": 1,
                "completed_games": 1,
                "completion_rate": 1.0,
                "avg_rounds_per_game": 3.0,
                "information_leak_count": 0,
                "phase_order_violation_count": 0,
                "role_skill_violation_count": 0,
                "top_errors": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text(
        json.dumps({"scenarios": [{"name": "smoke_6p_basic"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    game_dir = run_dir / "games" / "g0"
    game_dir.mkdir(parents=True)
    (game_dir / "post_game_manifest.json").write_text(
        json.dumps({"context": {"winner_camp": "villager"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (game_dir / "mvp_scores.json").write_text('{"summary": {"mvp_score": 0.5}}', encoding="utf-8")
    (game_dir / "benefit_scores.json").write_text('{"summary": {"total_score": 0.4}}', encoding="utf-8")
    (game_dir / "intention_scores.json").write_text('{"summary": {"avg_score": 0.3}}', encoding="utf-8")


def test_leaderboard_cli_entry_command(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_a"
    _write_run_fixture(run_dir)
    assert main(["entry", str(run_dir), "--model", "demo"]) == 0
    assert (run_dir / "leaderboard_entry.json").is_file()


def test_leaderboard_cli_build_command(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_a"
    _write_run_fixture(run_dir)
    main(["entry", str(run_dir)])
    out_dir = tmp_path / "board"
    assert main(["build", str(tmp_path), "--output-dir", str(out_dir)]) == 0
    assert (out_dir / "leaderboard.json").is_file()


def test_leaderboard_cli_compare_command(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    _write_run_fixture(run_a)
    _write_run_fixture(run_b)
    main(["entry", str(run_a), "--version-id", "a"])
    main(["entry", str(run_b), "--version-id", "b"])
    out_dir = tmp_path / "compare"
    assert main(
        [
            "compare",
            str(run_a / "leaderboard_entry.json"),
            str(run_b / "leaderboard_entry.json"),
            "--output-dir",
            str(out_dir),
        ]
    ) == 0
    assert list(out_dir.glob("ab_*.json"))
