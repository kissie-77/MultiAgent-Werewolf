from collections import Counter

from llm_werewolf.evaluation.models import EvaluationSummary, GameRunResult


def build_summary(results: list[GameRunResult]) -> EvaluationSummary:
    """Aggregate per-game results into evaluation metrics."""
    checker_failures = Counter(
        check.checker for result in results for check in result.checks if not check.passed
    )
    error_messages = Counter(
        result.error_message for result in results if result.error_message
    )
    failed_messages = Counter(
        check.message for result in results for check in result.checks if not check.passed
    )
    runtime_error_checks = [
        check
        for result in results
        for check in result.checks
        if not check.passed and check.checker == "RuntimeErrorEventChecker"
    ]
    top_errors = [
        message
        for message, _count in (error_messages + failed_messages).most_common(5)
        if message
    ]

    total_games = len(results)
    avg_rounds = (
        sum(result.rounds_played for result in results) / total_games if total_games else 0.0
    )

    return EvaluationSummary(
        total_games=total_games,
        completed_games=sum(1 for result in results if result.completed),
        crashed_games=sum(1 for result in results if result.crashed),
        timeout_games=sum(1 for result in results if result.timed_out),
        avg_rounds_per_game=avg_rounds,
        role_skill_violation_count=checker_failures["RoleSkillChecker"],
        information_leak_count=checker_failures["InformationIsolationChecker"],
        victory_rule_violation_count=checker_failures["VictoryCheckerEvaluator"],
        phase_order_violation_count=checker_failures["AsyncFlowChecker"],
        exception_count_by_role=dict(
            Counter(check.data.get("role_name") or "unknown" for check in runtime_error_checks)
        ),
        exception_count_by_phase=dict(
            Counter(check.data.get("phase") or "unknown" for check in runtime_error_checks)
        ),
        missing_structured_event_count=sum(
            1
            for result in results
            for check in result.checks
            if not check.passed
            and check.checker == "RoleSkillChecker"
            and check.data.get("missing_fields")
        ),
        top_errors=top_errors,
    )
