from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.evolution.runner import run_evolution_cycle


def run_evolution_matrix(
    *,
    output_root: str | Path,
    scenarios: list[str],
    seeds: list[int],
    rounds: int = 2,
    games_per_round: int = 3,
    timeout_seconds: float = 30.0,
    model: str = "unknown",
    prompt_version: str = "v2",
    initial_skill_version: str = "baseline",
    notes: list[str] | None = None,
) -> Path:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []

    for scenario in scenarios:
        for seed in seeds:
            run_root = root / _matrix_run_dir_name(scenario, seed)
            summary_path = run_evolution_cycle(
                output_root=run_root,
                scenario=scenario,
                rounds=rounds,
                games_per_round=games_per_round,
                timeout_seconds=timeout_seconds,
                seed=seed,
                model=model,
                prompt_version=prompt_version,
                initial_skill_version=initial_skill_version,
                notes=notes,
            )
            runs.append(_build_matrix_run_summary(scenario, seed, run_root, summary_path))

    return _write_matrix_summary(root, runs)


def _matrix_run_dir_name(scenario: str, seed: int) -> str:
    clean = "".join(ch if ch.isalnum() else "_" for ch in scenario.lower()).strip("_")
    return f"{clean}_seed_{seed}"


def _build_matrix_run_summary(
    scenario: str,
    seed: int,
    run_root: Path,
    summary_path: Path,
) -> dict[str, Any]:
    summary = _read_json(summary_path)
    rounds = [row for row in summary.get("rounds") or [] if isinstance(row, dict)]
    first_entry = _read_json(Path(rounds[0]["run_dir"]) / "leaderboard_entry.json") if rounds else {}
    final_entry = _read_json(Path(rounds[-1]["run_dir"]) / "leaderboard_entry.json") if rounds else {}
    ab_report = _read_json(Path(str(summary.get("ab_report_path")))) if summary.get("ab_report_path") else {}
    return {
        "scenario": scenario,
        "seed": seed,
        "run_root": str(run_root),
        "summary_path": str(summary_path),
        "initial_version_id": first_entry.get("version_id"),
        "final_version_id": final_entry.get("version_id"),
        "initial_win_rate": first_entry.get("win_rate"),
        "final_win_rate": final_entry.get("win_rate"),
        "win_rate_delta": (
            float(final_entry.get("win_rate", 0.0)) - float(first_entry.get("win_rate", 0.0))
            if first_entry and final_entry
            else None
        ),
        "initial_completion_rate": first_entry.get("completion_rate"),
        "final_completion_rate": final_entry.get("completion_rate"),
        "ab_recommendation": ab_report.get("recommendation"),
        "ab_win_rate_p_value": ab_report.get("win_rate_p_value"),
        "ab_win_rate_significant": ab_report.get("win_rate_significant"),
    }


def _write_matrix_summary(root: Path, runs: list[dict[str, Any]]) -> Path:
    payload = {
        "schema": "evolution_matrix_summary_v1",
        "run_count": len(runs),
        "scenarios": sorted({str(row.get("scenario")) for row in runs}),
        "seeds": sorted({int(row.get("seed")) for row in runs}),
        "runs": runs,
        "by_scenario": _group_rows(runs, "scenario"),
        "by_seed": _group_rows(runs, "seed"),
        "overall": _summarize_rows(runs),
    }
    json_path = root / "evolution_matrix_summary.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_matrix_summary_md(root / "evolution_matrix_summary.md", payload)
    return json_path


def _group_rows(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get(field)), []).append(row)
    return [
        {"group_key": key, **_summarize_rows(items)}
        for key, items in sorted(grouped.items(), key=lambda item: item[0])
    ]


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [float(row["win_rate_delta"]) for row in rows if isinstance(row.get("win_rate_delta"), (int, float))]
    significant = [row for row in rows if row.get("ab_win_rate_significant") is True]
    recommend_b = [row for row in rows if row.get("ab_recommendation") == "recommend_b"]
    return {
        "run_count": len(rows),
        "avg_win_rate_delta": (sum(deltas) / len(deltas)) if deltas else None,
        "positive_delta_count": sum(1 for value in deltas if value > 0),
        "recommend_b_count": len(recommend_b),
        "significant_count": len(significant),
    }


def _write_matrix_summary_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Evolution Matrix Summary",
        "",
        f"- Runs: {payload.get('run_count')}",
        f"- Scenarios: {', '.join(payload.get('scenarios') or [])}",
        f"- Seeds: {', '.join(str(seed) for seed in payload.get('seeds') or [])}",
        f"- Avg win-rate delta: {_fmt_pct((payload.get('overall') or {}).get('avg_win_rate_delta'))}",
        "",
        "| scenario | seed | initial | final | win_delta | recommendation | significant |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload.get("runs") or []:
        lines.append(
            f"| {row.get('scenario')} | {row.get('seed')} | "
            f"{_fmt_pct(row.get('initial_win_rate'))} | {_fmt_pct(row.get('final_win_rate'))} | "
            f"{_fmt_pct(row.get('win_rate_delta'))} | {row.get('ab_recommendation')} | "
            f"{row.get('ab_win_rate_significant')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _fmt_pct(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"{float(value):.1%}"
