import asyncio
from pathlib import Path

from llm_werewolf.evaluation.core.runner import EvaluationRunner
from llm_werewolf.evaluation.core.scenarios import smoke_6p_basic


def test_runner_writes_artifacts_for_smoke_scenario(tmp_path: Path) -> None:
    scenario = smoke_6p_basic(seed=3, repetitions=1, timeout_seconds=20)
    runner = EvaluationRunner(output_dir=tmp_path, scenarios=[scenario])

    results = asyncio.run(runner.run())

    assert len(results) == 1
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "metrics.csv").exists()
    assert (tmp_path / "report.md").exists()

    game_dir = tmp_path / "games" / results[0].game_id
    assert (game_dir / "events.jsonl").exists()
    assert (game_dir / "snapshots.jsonl").exists()
    assert (game_dir / "checks.json").exists()
    assert (game_dir / "post_game_manifest.json").exists()
