import csv
import json
from pathlib import Path

from llm_werewolf.evaluation.models import EvaluationSummary, GameRunResult


class EvaluationReporter:
    """Writes aggregate evaluation reports."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, summary: EvaluationSummary, results: list[GameRunResult]) -> None:
        """Write JSON, CSV, and Markdown report artifacts."""
        self._write_summary(summary)
        self._write_metrics_csv(summary)
        self._write_report(summary, results)

    def _write_summary(self, summary: EvaluationSummary) -> None:
        path = self.output_dir / "summary.json"
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_metrics_csv(self, summary: EvaluationSummary) -> None:
        path = self.output_dir / "metrics.csv"
        fields = [
            "total_games",
            "completed_games",
            "completion_rate",
            "crashed_games",
            "crash_rate",
            "timeout_games",
            "timeout_rate",
            "avg_rounds_per_game",
            "role_skill_violation_count",
            "information_leak_count",
            "victory_rule_violation_count",
            "phase_order_violation_count",
            "invalid_action_count",
            "missing_structured_event_count",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerow({field: getattr(summary, field) for field in fields})

    def _write_report(self, summary: EvaluationSummary, results: list[GameRunResult]) -> None:
        lines = [
            "# Game Correctness Evaluation Report",
            "",
            f"Total games: {summary.total_games}",
            f"Completed games: {summary.completed_games} ({summary.completion_rate:.2%})",
            f"Crashed games: {summary.crashed_games} ({summary.crash_rate:.2%})",
            f"Timeout games: {summary.timeout_games} ({summary.timeout_rate:.2%})",
            f"Average rounds per game: {summary.avg_rounds_per_game:.2f}",
            "",
            "## Violations",
            "",
            f"- Role skill violations: {summary.role_skill_violation_count}",
            f"- Information leaks: {summary.information_leak_count}",
            f"- Victory rule violations: {summary.victory_rule_violation_count}",
            f"- Phase order violations: {summary.phase_order_violation_count}",
            f"- Missing structured events: {summary.missing_structured_event_count}",
            "",
            "## Top Errors",
            "",
        ]

        if summary.top_errors:
            lines.extend(f"- {message}" for message in summary.top_errors)
        else:
            lines.append("- None")

        lines.extend(["", "## Games", ""])
        for result in results:
            status = "completed" if result.completed else "failed"
            lines.append(
                f"- `{result.game_id}`: {status}, winner={result.winner}, "
                f"rounds={result.rounds_played}, failures={result.failure_count}"
            )

        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
