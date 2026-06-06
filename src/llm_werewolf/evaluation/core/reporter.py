import csv
import json
from pathlib import Path

from llm_werewolf.evaluation.core.models import GameRunResult, EvaluationSummary


class EvaluationReporter:
    """负责把汇总指标写成多种报告格式。

    第一版同时输出 JSON、CSV、Markdown：
    - JSON 给程序和后续 Web 页面读。
    - CSV 给表格工具或论文实验统计用。
    - Markdown 给开发者快速查看。
    """

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, summary: EvaluationSummary, results: list[GameRunResult]) -> None:
        """一次性写出所有汇总报告文件。"""
        self._write_summary(summary)
        self._write_metrics_csv(summary)
        self._write_report(summary, results)

    def _write_summary(self, summary: EvaluationSummary) -> None:
        """写机器可读的完整 summary。"""
        path = self.output_dir / "summary.json"
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_metrics_csv(self, summary: EvaluationSummary) -> None:
        """写单行 CSV 指标，方便横向比较多次评测。"""
        path = self.output_dir / "metrics.csv"
        # CSV 只放标量字段；dict/list 这类结构化内容保留在 summary.json 中。
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
        """写人类可读 Markdown 报告。"""
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

        # 每局只展示摘要，详细事件和快照由 games/<game_id>/ 下的文件承载。
        lines.extend(["", "## Games", ""])
        for result in results:
            status = "completed" if result.completed else "failed"
            lines.append(
                f"- `{result.game_id}`: {status}, winner={result.winner}, "
                f"rounds={result.rounds_played}, failures={result.failure_count}"
            )

        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
