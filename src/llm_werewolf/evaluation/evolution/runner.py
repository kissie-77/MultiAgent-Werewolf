from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.core.runner import EvaluationRunner
from llm_werewolf.evaluation.core.scenarios import get_scenario
from llm_werewolf.evaluation.evolution.version_manifest import (
    restore_active_skills_from_manifest,
    write_version_manifest,
)
from llm_werewolf.evaluation.leaderboard.ab_compare import write_ab_report
from llm_werewolf.evaluation.leaderboard.aggregator import write_leaderboard


@dataclass
class EvolutionRoundResult:
    round_index: int
    version_id: str
    run_dir: Path
    skill_version: str
    version_manifest_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "version_id": self.version_id,
            "run_dir": str(self.run_dir),
            "skill_version": self.skill_version,
            "version_manifest_path": (
                str(self.version_manifest_path) if self.version_manifest_path is not None else None
            ),
        }


def run_evolution_cycle(
    *,
    output_root: str | Path,
    scenario: str = "smoke_6p_basic",
    rounds: int = 2,
    games_per_round: int = 3,
    timeout_seconds: float = 30.0,
    seed: int = 1,
    model: str = "unknown",
    prompt_version: str = "unknown",
    initial_skill_version: str = "baseline",
    notes: list[str] | None = None,
) -> Path:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    round_results: list[EvolutionRoundResult] = []
    previous_run_dir: Path | None = None
    previous_version_manifest_path: Path | None = None

    for round_index in range(1, rounds + 1):
        version_id = _build_version_id(round_index)
        skill_version = (
            initial_skill_version if round_index == 1 else f"evolved_r{round_index}"
        )
        run_dir = root / version_id
        if previous_version_manifest_path is not None:
            restore_active_skills_from_manifest(previous_version_manifest_path)
        _run_single_round(
            run_dir=run_dir,
            scenario=scenario,
            games=games_per_round,
            timeout_seconds=timeout_seconds,
            seed=seed + (round_index - 1) * 100,
            version_id=version_id,
            model=model,
            prompt_version=prompt_version,
            skill_version=skill_version,
            notes=notes,
            previous_run_dir=str(previous_run_dir) if previous_run_dir is not None else None,
        )
        manifest_path = write_version_manifest(
            run_dir,
            version_id=version_id,
            prompt_version=prompt_version,
            model=model,
            reasoning_effort=None,
        )
        round_results.append(
            EvolutionRoundResult(
                round_index=round_index,
                version_id=version_id,
                run_dir=run_dir,
                skill_version=skill_version,
                version_manifest_path=manifest_path,
            )
        )
        previous_run_dir = run_dir
        previous_version_manifest_path = manifest_path

    leaderboard_path = write_leaderboard(root)
    ab_report_path = _write_initial_vs_final_ab(root, round_results)
    summary_path = _write_evolution_summary(
        root,
        scenario=scenario,
        rounds=round_results,
        leaderboard_path=leaderboard_path,
        ab_report_path=ab_report_path,
    )
    return summary_path


def _run_single_round(
    *,
    run_dir: Path,
    scenario: str,
    games: int,
    timeout_seconds: float,
    seed: int,
    version_id: str,
    model: str,
    prompt_version: str,
    skill_version: str,
    notes: list[str] | None,
    previous_run_dir: str | None,
) -> None:
    eval_scenario = get_scenario(
        name=scenario,
        games=games,
        seed=seed,
        timeout_seconds=timeout_seconds,
    )
    runner = EvaluationRunner(
        output_dir=run_dir,
        scenarios=[eval_scenario],
        version_id=version_id,
        model=model,
        prompt_version=prompt_version,
        skill_version=skill_version,
        notes=notes,
        previous_run_dir=previous_run_dir,
    )
    asyncio.run(runner.run())


def _write_initial_vs_final_ab(
    root: Path,
    rounds: list[EvolutionRoundResult],
) -> Path | None:
    if len(rounds) < 2:
        return None
    first = rounds[0].run_dir / "leaderboard_entry.json"
    last = rounds[-1].run_dir / "leaderboard_entry.json"
    if not first.is_file() or not last.is_file():
        return None
    return write_ab_report(first, last, output_dir=root / "ab_reports")


def _write_evolution_summary(
    root: Path,
    *,
    scenario: str,
    rounds: list[EvolutionRoundResult],
    leaderboard_path: Path,
    ab_report_path: Path | None,
) -> Path:
    round_payloads = [round_result.to_dict() for round_result in rounds]
    round_summaries = _build_round_skill_summaries(rounds)
    payload = {
        "schema": "evolution_cycle_v1",
        "scenario": scenario,
        "round_count": len(rounds),
        "rounds": round_payloads,
        "round_skill_summaries": round_summaries,
        "version_diff_summaries": _build_version_diff_summaries(round_summaries),
        "leaderboard_path": str(leaderboard_path),
        "ab_report_path": str(ab_report_path) if ab_report_path is not None else None,
    }
    path = root / "evolution_summary.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _build_version_id(round_index: int) -> str:
    if round_index == 1:
        return "v1_initial"
    return f"v{round_index}_evolved"


def _build_round_skill_summaries(rounds: list[EvolutionRoundResult]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    previous_ids: set[str] = set()
    for round_result in rounds:
        manifest_path = round_result.version_manifest_path
        active_skills = _load_manifest_active_skills(manifest_path) if manifest_path is not None else {}
        current_ids = {
            str(item.get("skill_id") or "")
            for items in active_skills.values()
            for item in items
            if str(item.get("skill_id") or "")
        }
        out.append(
            {
                "version_id": round_result.version_id,
                "active_skill_count": len(current_ids),
                "active_skill_counts_by_role": {
                    role: len(items) for role, items in sorted(active_skills.items())
                },
                "added_skill_ids": sorted(current_ids - previous_ids),
                "removed_skill_ids": sorted(previous_ids - current_ids),
            }
        )
        previous_ids = current_ids
    return out


def _load_manifest_active_skills(manifest_path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    active_skills = payload.get("active_skills")
    if not isinstance(active_skills, dict):
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for role, items in active_skills.items():
        if not isinstance(items, list):
            continue
        out[str(role)] = [item for item in items if isinstance(item, dict)]
    return out


def _build_version_diff_summaries(
    round_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    previous_version_id: str | None = None
    previous_role_counts: dict[str, int] = {}
    for summary in round_summaries:
        current_role_counts = {
            str(role): int(count)
            for role, count in dict(summary.get("active_skill_counts_by_role") or {}).items()
        }
        role_changes: dict[str, dict[str, int]] = {}
        for role in sorted(set(previous_role_counts) | set(current_role_counts)):
            before = previous_role_counts.get(role, 0)
            after = current_role_counts.get(role, 0)
            if before != after:
                role_changes[role] = {
                    "before": before,
                    "after": after,
                    "delta": after - before,
                }
        out.append(
            {
                "version_id": summary.get("version_id"),
                "previous_version_id": previous_version_id,
                "added_skill_ids": list(summary.get("added_skill_ids") or []),
                "removed_skill_ids": list(summary.get("removed_skill_ids") or []),
                "role_count_changes": role_changes,
                "net_active_skill_delta": int(summary.get("active_skill_count") or 0)
                - sum(previous_role_counts.values()),
            }
        )
        previous_version_id = str(summary.get("version_id") or "")
        previous_role_counts = current_role_counts
    return out
