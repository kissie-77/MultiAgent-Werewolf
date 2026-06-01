"""A/B comparison for leaderboard entries."""

from __future__ import annotations

import json
import math
from pathlib import Path

from llm_werewolf.evaluation.leaderboard.models import ABReport


def compare_entries(entry_a: dict, entry_b: dict) -> ABReport:
    games_a = int(entry_a.get("games", 0))
    games_b = int(entry_b.get("games", 0))
    wins_a = _wins_from_entry(entry_a)
    wins_b = _wins_from_entry(entry_b)
    win_rate_a = float(entry_a.get("win_rate", 0.0))
    win_rate_b = float(entry_b.get("win_rate", 0.0))
    win_delta = win_rate_b - win_rate_a
    completion_a = float(entry_a.get("completion_rate", 0.0))
    completion_b = float(entry_b.get("completion_rate", 0.0))
    p_value = _two_proportion_z_p_value(wins_a, games_a, wins_b, games_b)
    significant = p_value is not None and p_value < 0.05

    if win_delta > 0.05 and completion_b >= completion_a and significant:
        recommendation = "recommend_b"
        summary = "B improves win rate with statistical significance and no completion-rate drop."
    elif win_delta > 0.05 and completion_b >= completion_a:
        recommendation = "recommend_b"
        summary = "B has an engineering-level win-rate lift, but significance is not proven yet."
    elif completion_b + 0.05 < completion_a:
        recommendation = "reject_b"
        summary = "B has a clear completion-rate drop, so it should not replace A."
    else:
        recommendation = "no_clear_winner"
        summary = "No clear winner yet; run more games or broaden scenarios."

    return ABReport(
        schema="ab_report_v1",
        version_a=str(entry_a.get("version_id")),
        version_b=str(entry_b.get("version_id")),
        games_a=games_a,
        games_b=games_b,
        win_rate_a=win_rate_a,
        win_rate_b=win_rate_b,
        win_rate_delta=win_delta,
        avg_mvp_score_a=_optional_float(entry_a.get("avg_mvp_score")),
        avg_mvp_score_b=_optional_float(entry_b.get("avg_mvp_score")),
        avg_benefit_score_a=_optional_float(entry_a.get("avg_benefit_score")),
        avg_benefit_score_b=_optional_float(entry_b.get("avg_benefit_score")),
        avg_intention_score_a=_optional_float(entry_a.get("avg_intention_score")),
        avg_intention_score_b=_optional_float(entry_b.get("avg_intention_score")),
        completion_rate_a=completion_a,
        completion_rate_b=completion_b,
        wins_a=wins_a,
        wins_b=wins_b,
        win_rate_ci_a=_wilson_interval(wins_a, games_a),
        win_rate_ci_b=_wilson_interval(wins_b, games_b),
        win_rate_p_value=p_value,
        win_rate_significant=significant,
        significance_method="two_proportion_z_test_with_wilson_ci",
        recommendation=recommendation,
        summary=summary,
    )


def write_ab_report(
    entry_a_path: str | Path,
    entry_b_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> Path:
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
        "",
        "## Significance",
        "",
        f"- Method: `{report.significance_method}`",
        f"- Wins: A `{report.wins_a}/{report.games_a}`, B `{report.wins_b}/{report.games_b}`",
        f"- Win-rate 95% CI: A `{_ci(report.win_rate_ci_a)}`, B `{_ci(report.win_rate_ci_b)}`",
        f"- p-value: `{_p_value(report.win_rate_p_value)}`",
        f"- Significant at 0.05: `{report.win_rate_significant}`",
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


def _wins_from_entry(entry: dict) -> int:
    if isinstance(entry.get("wins"), int):
        return int(entry["wins"])
    games = int(entry.get("games", 0))
    win_rate = float(entry.get("win_rate", 0.0))
    return int(round(games * win_rate))


def _wilson_interval(
    wins: int,
    games: int,
    z: float = 1.959963984540054,
) -> tuple[float, float]:
    if games <= 0:
        return (0.0, 0.0)
    phat = wins / games
    denom = 1.0 + z * z / games
    center = (phat + z * z / (2.0 * games)) / denom
    margin = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * games)) / games) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _two_proportion_z_p_value(
    wins_a: int,
    games_a: int,
    wins_b: int,
    games_b: int,
) -> float | None:
    if games_a <= 0 or games_b <= 0:
        return None
    pooled = (wins_a + wins_b) / (games_a + games_b)
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / games_a + 1.0 / games_b))
    if se == 0.0:
        return 1.0
    z_score = ((wins_b / games_b) - (wins_a / games_a)) / se
    return math.erfc(abs(z_score) / math.sqrt(2.0))


def _ci(value: tuple[float, float]) -> str:
    return f"{value[0]:.1%} - {value[1]:.1%}"


def _p_value(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"
