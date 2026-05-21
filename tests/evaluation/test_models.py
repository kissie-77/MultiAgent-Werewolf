from llm_werewolf.evaluation.models import (
    CheckResult,
    CheckSeverity,
    EvaluationSummary,
    GameRunResult,
)


def test_check_result_defaults() -> None:
    result = CheckResult(
        checker="AsyncFlowChecker",
        passed=False,
        message="Illegal phase transition",
    )

    assert result.severity == CheckSeverity.ERROR
    assert result.data == {}


def test_game_run_result_flags_failures() -> None:
    run = GameRunResult(
        game_id="game-1",
        scenario_name="smoke_6p_basic",
        seed=7,
        completed=False,
        crashed=True,
        timed_out=False,
        winner=None,
        rounds_played=1,
        duration_seconds=0.5,
        checks=[
            CheckResult(
                checker="InformationIsolationChecker",
                passed=False,
                message="Private event leaked",
                severity=CheckSeverity.CRITICAL,
            )
        ],
    )

    assert run.has_failures
    assert run.failure_count == 1


def test_evaluation_summary_rates() -> None:
    summary = EvaluationSummary(
        total_games=4,
        completed_games=2,
        crashed_games=1,
        timeout_games=1,
        avg_rounds_per_game=2.5,
    )

    assert summary.completion_rate == 0.5
    assert summary.crash_rate == 0.25
    assert summary.timeout_rate == 0.25


def test_evaluation_summary_zero_games_rates() -> None:
    summary = EvaluationSummary(total_games=0)

    assert summary.completion_rate == 0.0
    assert summary.crash_rate == 0.0
    assert summary.timeout_rate == 0.0
