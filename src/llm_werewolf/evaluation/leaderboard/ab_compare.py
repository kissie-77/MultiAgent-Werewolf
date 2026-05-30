"""A/B comparison for leaderboard entries."""

from __future__ import annotations

import json
from pathlib import Path

from llm_werewolf.evaluation.leaderboard.models import ABReport


def compare_entries(entry_a: dict, entry_b: dict) -> ABReport:
    win_delta = float(entry_b.get("win_rate", 0.0)) - float(entry_a.get("win_rate", 0.0))
    completion_a = float(entry_a.get("completion_rate", 0.0))
    completion_b = float(entry_b.get("completion_rate", 0.0))

    if win_delta > 0.05 and completion_b >= completion_a:
        recommendation = "recommend_b"
        summary = "B 版本在胜率上有明显提升，且完成率没有下降。"
    elif completion_b + 0.05 < completion_a:
        recommendation = "reject_b"
        summary = "B 版本完成率明显下降，不建议替换当前版本。"
    else:
        recommendation = "no_clear_winner"
        summary = "两个版本差异不够明显，建议继续观察或扩大样本。"

    return ABReport(
        schema="ab_report_v1",
        version_a=str(entry_a.get("version_id")),
        version_b=str(entry_b.get("version_id")),
        games_a=int(entry_a.get("games", 0)),
        games_b=int(entry_b.get("games", 0)),
        win_rate_a=float(entry_a.get("win_rate", 0.0)),
        win_rate_b=float(entry_b.get("win_rate", 0.0)),
        win_rate_delta=win_delta,
        avg_mvp_score_a=_optional_float(entry_a.get("avg_mvp_score")),
        avg_mvp_score_b=_optional_float(entry_b.get("avg_mvp_score")),
        avg_benefit_score_a=_optional_float(entry_a.get("avg_benefit_score")),
        avg_benefit_score_b=_optional_float(entry_b.get("avg_benefit_score")),
        avg_intention_score_a=_optional_float(entry_a.get("avg_intention_score")),
        avg_intention_score_b=_optional_float(entry_b.get("avg_intention_score")),
        completion_rate_a=completion_a,
        completion_rate_b=completion_b,
        recommendation=recommendation,
        summary=summary,
    )


def write_ab_report(entry_a_path: str | Path, entry_b_path: str | Path, *, output_dir: str | Path | None = None) -> Path:
    path_a = Path(entry_a_path)
    path_b = Path(entry_b_path)
    entry_a = json.loads(path_a.read_text(encoding="utf-8"))
    entry_b = json.loads(path_b.read_text(encoding="utf-8"))
    report = compare_entries(entry_a, entry_b)

    out = Path(output_dir) if output_dir is not None else path_a.parent.parent / "ab_reports"
    out.mkdir(parents=True, exist_ok=True)
    stem = f"ab_{entry_a['version_id']}_vs_{entry_b['version_id']}"

    json_path = out / f"{stem}.json"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = out / f"{stem}.md"
    md_lines = [
        f"# A/B Report: {entry_a['version_id']} vs {entry_b['version_id']}",
        "",
        f"- Recommendation: `{report.recommendation}`",
        f"- Summary: {report.summary}",
        "",
        "| metric | A | B | delta |",
        "| --- | ---: | ---: | ---: |",
        f"| win_rate | {_pct(report.win_rate_a)} | {_pct(report.win_rate_b)} | {_pct(report.win_rate_delta)} |",
        f"| completion_rate | {_pct(report.completion_rate_a)} | {_pct(report.completion_rate_b)} | {_pct(report.completion_rate_b - report.completion_rate_a)} |",
        f"| avg_mvp_score | {_fmt(report.avg_mvp_score_a)} | {_fmt(report.avg_mvp_score_b)} | {_delta(report.avg_mvp_score_a, report.avg_mvp_score_b)} |",
        f"| avg_benefit_score | {_fmt(report.avg_benefit_score_a)} | {_fmt(report.avg_benefit_score_b)} | {_delta(report.avg_benefit_score_a, report.avg_benefit_score_b)} |",
        f"| avg_intention_score | {_fmt(report.avg_intention_score_a)} | {_fmt(report.avg_intention_score_b)} | {_delta(report.avg_intention_score_a, report.avg_intention_score_b)} |",
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path


def _optional_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _delta(before: float | None, after: float | None) -> str:
    if before is None or after is None:
        return "-"
    return f"{after - before:+.3f}"
