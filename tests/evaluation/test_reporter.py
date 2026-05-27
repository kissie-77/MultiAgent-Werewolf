import json
from pathlib import Path

from llm_werewolf.evaluation.core.metrics import build_summary
from llm_werewolf.evaluation.core.models import CheckResult, GameRunResult
from llm_werewolf.evaluation.core.reporter import EvaluationReporter


def test_build_summary_counts_rates_and_checker_failures() -> None:
    results = [
        GameRunResult(
            game_id="game-1",
            scenario_name="smoke",
            seed=1,
            completed=True,
            winner="villager",
            rounds_played=2,
            duration_seconds=1.0,
        ),
        GameRunResult(
            game_id="game-2",
            scenario_name="smoke",
            seed=2,
            completed=False,
            crashed=True,
            rounds_played=1,
            duration_seconds=0.5,
            error_message="boom",
            checks=[
                CheckResult(
                    checker="RuntimeErrorEventChecker",
                    passed=False,
                    message="role exploded",
                    data={"role_name": "Alpha Wolf", "phase": "night"},
                ),
                CheckResult(
                    checker="AsyncFlowChecker",
                    passed=False,
                    message="Illegal phase transition",
                ),
                CheckResult(
                    checker="InformationIsolationChecker",
                    passed=False,
                    message="Private leak",
                ),
            ],
        ),
    ]

    summary = build_summary(results)

    assert summary.total_games == 2
    assert summary.completed_games == 1
    assert summary.crashed_games == 1
    assert summary.completion_rate == 0.5
    assert summary.crash_rate == 0.5
    assert summary.phase_order_violation_count == 1
    assert summary.information_leak_count == 1
    assert summary.exception_count_by_role == {"Alpha Wolf": 1}
    assert summary.exception_count_by_phase == {"night": 1}
    assert summary.top_errors[0] == "boom"


def test_reporter_writes_summary_metrics_and_markdown(tmp_path: Path) -> None:
    results = [
        GameRunResult(
            game_id="game-1",
            scenario_name="smoke",
            seed=1,
            completed=True,
            winner="villager",
            rounds_played=2,
            duration_seconds=1.0,
        )
    ]
    summary = build_summary(results)

    EvaluationReporter(tmp_path).write(summary, results)

    summary_json = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    metrics_csv = (tmp_path / "metrics.csv").read_text(encoding="utf-8")
    report = (tmp_path / "report.md").read_text(encoding="utf-8")

    assert summary_json["total_games"] == 1
    assert "completion_rate" in metrics_csv
    assert "# Game Correctness Evaluation Report" in report
    assert "`game-1`" in report
