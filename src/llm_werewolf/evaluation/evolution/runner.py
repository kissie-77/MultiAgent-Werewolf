from __future__ import annotations

import json
from typing import Any
import asyncio
from pathlib import Path
from dataclasses import dataclass

from llm_werewolf.evaluation.core.runner import EvaluationRunner
from llm_werewolf.evaluation.core.scenarios import get_scenario
from llm_werewolf.evaluation.leaderboard.ab_compare import write_ab_report
from llm_werewolf.evaluation.leaderboard.aggregator import write_leaderboard
from llm_werewolf.evaluation.evolution.prompt_evolver import (
    PromptEvolutionResult,
    evolve_prompt_from_run,
)
from llm_werewolf.evaluation.evolution.version_manifest import (
    write_version_manifest,
    restore_runtime_from_manifest,
)
from llm_werewolf.strategy.registry.role_version_manifest import (
    RoleVersionManifest,
    set_active_manifest,
)


@dataclass
class EvolutionRoundResult:
    round_index: int
    version_id: str
    run_dir: Path
    skill_version: str
    prompt_version: str
    version_manifest_path: Path | None = None
    prompt_evolution: PromptEvolutionResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "version_id": self.version_id,
            "run_dir": str(self.run_dir),
            "skill_version": self.skill_version,
            "prompt_version": self.prompt_version,
            "version_manifest_path": (
                str(self.version_manifest_path) if self.version_manifest_path is not None else None
            ),
            "prompt_evolution": (
                {
                    "base_prompt_version": self.prompt_evolution.base_prompt_version,
                    "new_prompt_version": self.prompt_evolution.new_prompt_version,
                    "new_version_dir": (
                        str(self.prompt_evolution.new_version_dir)
                        if self.prompt_evolution.new_version_dir is not None
                        else None
                    ),
                    "applied_count": self.prompt_evolution.applied_count,
                    "applied_path": str(self.prompt_evolution.applied_path),
                    "diff_path": str(self.prompt_evolution.diff_path),
                }
                if self.prompt_evolution is not None
                else None
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
    prompt_version: str = "v1",
    initial_skill_version: str = "v1",
    notes: list[str] | None = None,
) -> Path:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    round_results: list[EvolutionRoundResult] = []
    previous_run_dir: Path | None = None
    previous_version_manifest_path: Path | None = None
    role_manifest = RoleVersionManifest(
        default_prompt_version=prompt_version,
        default_skill_version=initial_skill_version,
    )
    set_active_manifest(role_manifest)

    for round_index in range(1, rounds + 1):
        version_id = _build_version_id(round_index)
        skill_version = (
            initial_skill_version if round_index == 1 else f"v{round_index}"
        )
        run_dir = root / version_id
        if previous_version_manifest_path is not None:
            role_manifest = restore_runtime_from_manifest(previous_version_manifest_path)
        else:
            set_active_manifest(role_manifest)
        _run_single_round(
            run_dir=run_dir,
            scenario=scenario,
            games=games_per_round,
            timeout_seconds=timeout_seconds,
            seed=seed + (round_index - 1) * 100,
            version_id=version_id,
            model=model,
            role_manifest=role_manifest,
            skill_version=skill_version,
            notes=notes,
            previous_run_dir=str(previous_run_dir) if previous_run_dir is not None else None,
        )
        prompt_evolution = evolve_prompt_from_run(
            run_dir,
            role_version_manifest=role_manifest,
            output_root=root / "prompt_roles",
        )
        if prompt_evolution.role_version_manifest:
            role_manifest = RoleVersionManifest.from_dict(prompt_evolution.role_version_manifest)
            set_active_manifest(role_manifest)
        manifest_path = write_version_manifest(
            run_dir,
            version_id=version_id,
            prompt_version=role_manifest.default_prompt_version,
            model=model,
            reasoning_effort=None,
            prompt_evolution=prompt_evolution.to_dict(),
            role_version_manifest=role_manifest,
        )
        round_results.append(
            EvolutionRoundResult(
                round_index=round_index,
                version_id=version_id,
                run_dir=run_dir,
                skill_version=skill_version,
                prompt_version=role_manifest.default_prompt_version,
                version_manifest_path=manifest_path,
                prompt_evolution=prompt_evolution,
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
    role_manifest: RoleVersionManifest,
    skill_version: str,
    notes: list[str] | None,
    previous_run_dir: str | None,
) -> None:
    set_active_manifest(role_manifest)
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
        prompt_version=role_manifest.default_prompt_version,
        skill_version=skill_version,
        notes=notes,
        previous_run_dir=previous_run_dir,
        role_version_manifest=role_manifest,
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
        "prompt_version_chain": _build_prompt_version_chain(rounds),
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


def _build_prompt_version_chain(rounds: list[EvolutionRoundResult]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for round_result in rounds:
        evolution = round_result.prompt_evolution
        out.append(
            {
                "version_id": round_result.version_id,
                "runtime_prompt_version": round_result.prompt_version,
                "next_prompt_version": (
                    evolution.new_prompt_version if evolution is not None else round_result.prompt_version
                ),
                "applied_prompt_proposal_count": evolution.applied_count if evolution is not None else 0,
                "prompt_version_changed": (
                    evolution is not None
                    and evolution.new_prompt_version != round_result.prompt_version
                ),
                "prompt_diff_path": str(evolution.diff_path) if evolution is not None else None,
            }
        )
    return out
