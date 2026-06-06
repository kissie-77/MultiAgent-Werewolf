import json
from pathlib import Path

from llm_werewolf.evaluation.evolution import matrix_runner


def test_run_evolution_matrix_writes_grouped_summary(tmp_path: Path, monkeypatch) -> None:
    def fake_run_evolution_cycle(
        *,
        output_root: str | Path,
        scenario: str,
        rounds: int,
        games_per_round: int,
        timeout_seconds: float,
        seed: int,
        model: str,
        prompt_version: str,
        initial_skill_version: str,
        notes: list[str] | None,
    ) -> Path:
        _ = rounds, games_per_round, timeout_seconds, model, prompt_version, initial_skill_version, notes
        root = Path(output_root)
        first = root / "v1_initial"
        final = root / "v2_evolved"
        ab_dir = root / "ab_reports"
        first.mkdir(parents=True, exist_ok=True)
        final.mkdir(parents=True, exist_ok=True)
        ab_dir.mkdir(parents=True, exist_ok=True)
        first.joinpath("leaderboard_entry.json").write_text(
            json.dumps(
                {
                    "version_id": "v1_initial",
                    "scenario": scenario,
                    "games": 10,
                    "win_rate": 0.4,
                    "completion_rate": 1.0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        final.joinpath("leaderboard_entry.json").write_text(
            json.dumps(
                {
                    "version_id": "v2_evolved",
                    "scenario": scenario,
                    "games": 10,
                    "win_rate": 0.6,
                    "completion_rate": 1.0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        ab_path = ab_dir / "ab_v1_initial_vs_v2_evolved.json"
        ab_path.write_text(
            json.dumps(
                {
                    "recommendation": "recommend_b",
                    "win_rate_p_value": 0.12,
                    "win_rate_significant": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        summary_path = root / "evolution_summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "schema": "evolution_cycle_v1",
                    "rounds": [
                        {"run_dir": str(first)},
                        {"run_dir": str(final)},
                    ],
                    "ab_report_path": str(ab_path),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        seed_path = root / "seed.txt"
        seed_path.write_text(str(seed), encoding="utf-8")
        return summary_path

    monkeypatch.setattr(matrix_runner, "run_evolution_cycle", fake_run_evolution_cycle)

    path = matrix_runner.run_evolution_matrix(
        output_root=tmp_path,
        scenarios=["smoke_6p_basic", "regression_default_demo"],
        seeds=[1, 2],
        rounds=2,
        games_per_round=1,
        timeout_seconds=20,
        model="demo",
        prompt_version="v2",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "evolution_matrix_summary_v1"
    assert payload["run_count"] == 4
    assert payload["overall"]["positive_delta_count"] == 4
    assert len(payload["by_scenario"]) == 2
    assert len(payload["by_seed"]) == 2
    assert (tmp_path / "evolution_matrix_summary.md").is_file()
