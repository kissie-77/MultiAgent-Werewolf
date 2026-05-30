"""Aggregate leaderboard entries into json/csv/markdown outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def collect_entries(root_dir: str | Path) -> list[dict]:
    root = Path(root_dir)
    entries: list[dict] = []
    for path in root.rglob("leaderboard_entry.json"):
        entries.append(json.loads(path.read_text(encoding="utf-8")))
    entries.sort(key=lambda item: (item.get("win_rate", 0.0), item.get("completion_rate", 0.0)), reverse=True)
    return entries


def write_leaderboard(root_dir: str | Path, *, output_dir: str | Path | None = None) -> Path:
    root = Path(root_dir)
    out = Path(output_dir) if output_dir is not None else root / "leaderboards"
    out.mkdir(parents=True, exist_ok=True)
    entries = collect_entries(root)

    json_path = out / "leaderboard.json"
    json_path.write_text(
        json.dumps({"schema": "leaderboard_v1", "entries": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_path = out / "leaderboard.csv"
    fields = [
        "version_id",
        "model",
        "prompt_version",
        "skill_version",
        "scenario",
        "games",
        "completed_games",
        "completion_rate",
        "win_rate",
        "avg_rounds",
        "avg_mvp_score",
        "avg_benefit_score",
        "avg_intention_score",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for entry in entries:
            writer.writerow({field: entry.get(field) for field in fields})

    md_path = out / "leaderboard.md"
    lines = [
        "# Leaderboard",
        "",
        "| rank | version_id | model | prompt | skill_version | games | completion_rate | win_rate | avg_mvp | avg_benefit | avg_intention |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for idx, entry in enumerate(entries, start=1):
        lines.append(
            f"| {idx} | {entry.get('version_id')} | {entry.get('model')} | {entry.get('prompt_version')} | "
            f"{entry.get('skill_version')} | {entry.get('games')} | "
            f"{_pct(entry.get('completion_rate'))} | {_pct(entry.get('win_rate'))} | "
            f"{_fmt(entry.get('avg_mvp_score'))} | {_fmt(entry.get('avg_benefit_score'))} | {_fmt(entry.get('avg_intention_score'))} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    grouped_payloads = _write_grouped_leaderboards(out, entries)
    _write_best_summary(out, grouped_payloads)
    return json_path


def _write_grouped_leaderboards(out: Path, entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped_specs = [
        ("model", "model_leaderboard"),
        ("prompt_version", "prompt_leaderboard"),
        ("skill_version", "skill_leaderboard"),
    ]
    grouped_payloads: dict[str, list[dict[str, Any]]] = {}
    for field, basename in grouped_specs:
        groups = _build_grouped_rows(entries, field)
        _write_grouped_json(out / f"{basename}.json", field, groups)
        _write_grouped_csv(out / f"{basename}.csv", field, groups)
        _write_grouped_md(out / f"{basename}.md", field, groups)
        grouped_payloads[field] = groups
    return grouped_payloads


def _build_grouped_rows(entries: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        key = str(entry.get(field) or "unknown")
        buckets.setdefault(key, []).append(entry)

    rows: list[dict[str, Any]] = []
    for key, bucket in buckets.items():
        sorted_bucket = sorted(
            bucket,
            key=lambda item: (item.get("win_rate", 0.0), item.get("completion_rate", 0.0)),
            reverse=True,
        )
        best = sorted_bucket[0]
        rows.append(
            {
                "group_key": key,
                "entry_count": len(bucket),
                "total_games": sum(int(item.get("games", 0) or 0) for item in bucket),
                "avg_win_rate": _avg(bucket, "win_rate"),
                "avg_completion_rate": _avg(bucket, "completion_rate"),
                "avg_mvp_score": _avg(bucket, "avg_mvp_score"),
                "avg_benefit_score": _avg(bucket, "avg_benefit_score"),
                "avg_intention_score": _avg(bucket, "avg_intention_score"),
                "best_version_id": str(best.get("version_id") or ""),
                "best_scenario": str(best.get("scenario") or "unknown"),
                "best_win_rate": best.get("win_rate"),
                "best_completion_rate": best.get("completion_rate"),
            }
        )

    rows.sort(
        key=lambda item: (
            item.get("avg_win_rate", 0.0) or 0.0,
            item.get("avg_completion_rate", 0.0) or 0.0,
        ),
        reverse=True,
    )
    return rows


def _write_grouped_json(path: Path, field: str, groups: list[dict[str, Any]]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "grouped_leaderboard_v1",
                "group_by": field,
                "groups": groups,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_grouped_csv(path: Path, field: str, groups: list[dict[str, Any]]) -> None:
    fields = [
        "group_key",
        "entry_count",
        "total_games",
        "avg_win_rate",
        "avg_completion_rate",
        "avg_mvp_score",
        "avg_benefit_score",
        "avg_intention_score",
        "best_version_id",
        "best_scenario",
        "best_win_rate",
        "best_completion_rate",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for group in groups:
            writer.writerow({field_name: group.get(field_name) for field_name in fields})


def _write_grouped_md(path: Path, field: str, groups: list[dict[str, Any]]) -> None:
    title = _group_title(field)
    lines = [
        f"# {title}",
        "",
        f"| rank | {field} | entries | total_games | avg_win_rate | avg_completion_rate | best_version | best_win_rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for idx, group in enumerate(groups, start=1):
        lines.append(
            f"| {idx} | {group.get('group_key')} | {group.get('entry_count')} | {group.get('total_games')} | "
            f"{_pct(group.get('avg_win_rate'))} | {_pct(group.get('avg_completion_rate'))} | "
            f"{group.get('best_version_id')} | {_pct(group.get('best_win_rate'))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_best_summary(out: Path, grouped_payloads: dict[str, list[dict[str, Any]]]) -> None:
    summary = {
        "schema": "leaderboard_best_summary_v1",
        "best_model_group": _best_group_payload("model", grouped_payloads.get("model", [])),
        "best_prompt_group": _best_group_payload("prompt_version", grouped_payloads.get("prompt_version", [])),
        "best_skill_group": _best_group_payload("skill_version", grouped_payloads.get("skill_version", [])),
    }
    (out / "best_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Best Version Summary",
        "",
        _render_best_summary_line("Model", summary["best_model_group"]),
        _render_best_summary_line("Prompt", summary["best_prompt_group"]),
        _render_best_summary_line("Skill", summary["best_skill_group"]),
    ]
    (out / "best_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _best_group_payload(field: str, groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not groups:
        return None
    best = groups[0]
    return {
        "group_by": field,
        "group_key": best.get("group_key"),
        "best_version_id": best.get("best_version_id"),
        "best_scenario": best.get("best_scenario"),
        "avg_win_rate": best.get("avg_win_rate"),
        "avg_completion_rate": best.get("avg_completion_rate"),
        "best_win_rate": best.get("best_win_rate"),
        "entry_count": best.get("entry_count"),
        "total_games": best.get("total_games"),
    }


def _render_best_summary_line(label: str, payload: dict[str, Any] | None) -> str:
    if payload is None:
        return f"- {label}: no data"
    return (
        f"- {label}: {payload.get('group_key')} | best_version={payload.get('best_version_id')} | "
        f"avg_win_rate={_pct(payload.get('avg_win_rate'))} | "
        f"best_win_rate={_pct(payload.get('best_win_rate'))} | "
        f"games={payload.get('total_games')}"
    )


def _group_title(field: str) -> str:
    if field == "model":
        return "Model Leaderboard"
    if field == "prompt_version":
        return "Prompt Leaderboard"
    if field == "skill_version":
        return "Skill Leaderboard"
    return f"{field} Leaderboard"


def _avg(entries: list[dict[str, Any]], field: str) -> float | None:
    values = [float(item[field]) for item in entries if isinstance(item.get(field), (int, float))]
    if not values:
        return None
    return sum(values) / len(values)


def _pct(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"{float(value):.1%}"


def _fmt(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"{float(value):.3f}"
