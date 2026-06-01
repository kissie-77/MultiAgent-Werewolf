from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from llm_werewolf.strategy.prompt_registry import (
    get_registry,
    register_prompt_search_root,
    resolve_prompt_version_dir,
)

PROMPT_VERSIONS_ROOT = Path("artifacts") / "prompt_versions"
SUPPORTED_KINDS = {"mvp_golden_quote", "positive_persuasion", "bad_case_rule"}
SUPPORTED_ACTIONS = {"append_guidance"}


@dataclass(frozen=True)
class PromptEvolutionResult:
    base_prompt_version: str
    new_prompt_version: str
    new_version_dir: Path | None
    applied_count: int
    applied_path: Path
    diff_path: Path


def evolve_prompt_from_run(
    run_dir: str | Path,
    *,
    base_prompt_version: str,
    output_root: str | Path = PROMPT_VERSIONS_ROOT,
    max_per_role: int = 2,
) -> PromptEvolutionResult:
    base = Path(run_dir)
    proposals_path = base / "prompt_proposals.json"
    output_base = Path(output_root)
    register_prompt_search_root(output_base)
    proposals_payload = _read_json(proposals_path)
    proposals = _select_proposals(proposals_payload, max_per_role=max_per_role)
    new_version = _build_next_prompt_version(base_prompt_version, base.name)

    applied_path = base / "applied_prompt_proposals.json"
    diff_path = base / "prompt_version_diff.json"

    if not proposals:
        _write_json(
            applied_path,
            {
                "schema": "applied_prompt_proposals_v1",
                "base_prompt_version": base_prompt_version,
                "new_prompt_version": base_prompt_version,
                "applied_count": 0,
                "applied": [],
                "skipped_reason": "no_applicable_prompt_proposals",
            },
        )
        _write_json(
            diff_path,
            {
                "schema": "prompt_version_diff_v1",
                "base_prompt_version": base_prompt_version,
                "new_prompt_version": base_prompt_version,
                "changes": [],
            },
        )
        return PromptEvolutionResult(
            base_prompt_version=base_prompt_version,
            new_prompt_version=base_prompt_version,
            new_version_dir=None,
            applied_count=0,
            applied_path=applied_path,
            diff_path=diff_path,
        )

    new_version_dir = output_base / new_version
    _copy_prompt_version(base_prompt_version, new_version, new_version_dir)
    registry = get_registry(new_version)
    changes = _apply_proposals(registry.version_dir, new_version, proposals)
    get_registry.cache_clear()

    _write_json(
        applied_path,
        {
            "schema": "applied_prompt_proposals_v1",
            "base_prompt_version": base_prompt_version,
            "new_prompt_version": new_version,
            "applied_count": len(proposals),
            "applied": proposals,
        },
    )
    _write_json(
        diff_path,
        {
            "schema": "prompt_version_diff_v1",
            "base_prompt_version": base_prompt_version,
            "new_prompt_version": new_version,
            "changes": changes,
        },
    )
    (base / "new_prompt_version.txt").write_text(new_version, encoding="utf-8")
    return PromptEvolutionResult(
        base_prompt_version=base_prompt_version,
        new_prompt_version=new_version,
        new_version_dir=new_version_dir,
        applied_count=len(proposals),
        applied_path=applied_path,
        diff_path=diff_path,
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _select_proposals(payload: dict[str, Any], *, max_per_role: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    seen: set[tuple[str, str, str]] = set()
    rows = [row for row in payload.get("proposals") or [] if isinstance(row, dict)]
    rows.sort(key=lambda row: int(row.get("priority") or 9999))
    for row in rows:
        if str(row.get("status") or "") != "draft":
            continue
        if str(row.get("kind") or "") not in SUPPORTED_KINDS:
            continue
        patch = row.get("suggested_patch") or {}
        if not isinstance(patch, dict):
            continue
        if str(patch.get("action") or "") not in SUPPORTED_ACTIONS:
            continue
        text = str(patch.get("text_zh") or "").strip()
        target = str(row.get("target_variable") or "").strip()
        section = str(patch.get("section") or "").strip()
        role_key = str(row.get("prompt_role_key") or "global")
        if not text or not target:
            continue
        if counts.get(role_key, 0) >= max_per_role:
            continue
        key = (target, section, text)
        if key in seen:
            continue
        seen.add(key)
        counts[role_key] = counts.get(role_key, 0) + 1
        selected.append(row)
    return selected


def _build_next_prompt_version(base_prompt_version: str, run_name: str) -> str:
    clean_run_name = "".join(ch if ch.isalnum() else "_" for ch in run_name.lower()).strip("_")
    return f"{base_prompt_version}_{clean_run_name}_prompt"


def _copy_prompt_version(base_prompt_version: str, new_prompt_version: str, target_dir: Path) -> None:
    source_dir = resolve_prompt_version_dir(base_prompt_version)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    manifest_path = target_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    manifest["version"] = new_prompt_version
    manifest["status"] = "generated"
    manifest["parent"] = base_prompt_version
    manifest["created_at"] = datetime.now(timezone.utc).date().isoformat()
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")

    variables_path = target_dir / "variables.yaml"
    variables = yaml.safe_load(variables_path.read_text(encoding="utf-8")) or {}
    raw_variables = variables.get("variables") or {}
    renamed: dict[str, Any] = {}
    for variable_id, meta in raw_variables.items():
        variable = str(variable_id)
        if variable.startswith(f"{base_prompt_version}."):
            variable = f"{new_prompt_version}.{variable[len(base_prompt_version) + 1:]}"
        renamed[variable] = meta
    variables["variables"] = renamed
    variables_path.write_text(yaml.safe_dump(variables, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _apply_proposals(
    version_dir: Path,
    new_prompt_version: str,
    proposals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    variables = yaml.safe_load((version_dir / "variables.yaml").read_text(encoding="utf-8")) or {}
    specs = variables.get("variables") or {}
    changes: list[dict[str, Any]] = []
    for proposal in proposals:
        target = _target_for_new_version(str(proposal.get("target_variable") or ""), new_prompt_version)
        spec = specs.get(target)
        if not isinstance(spec, dict):
            continue
        target_path = version_dir / str(spec.get("file") or "")
        patch = proposal.get("suggested_patch") or {}
        text = str(patch.get("text_zh") or "").strip()
        if not text:
            continue
        if spec.get("kind") == "role_card":
            _append_to_role_suggestion(target_path, text)
        else:
            _append_to_text_file(target_path, text)
        changes.append(
            {
                "proposal_id": proposal.get("proposal_id"),
                "target_variable": target,
                "section": patch.get("section"),
                "action": patch.get("action"),
                "text_zh": text,
            }
        )
    return changes


def _target_for_new_version(target_variable: str, new_prompt_version: str) -> str:
    parts = target_variable.split(".", 1)
    if len(parts) != 2:
        return target_variable
    return f"{new_prompt_version}.{parts[1]}"


def _append_to_role_suggestion(path: Path, text: str) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    current = str(data.get("suggestion") or "").strip()
    marker = f"\n\n[自动采纳的复盘建议]\n- {text}"
    data["suggestion"] = f"{current}{marker}" if current else text
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _append_to_text_file(path: Path, text: str) -> None:
    current = path.read_text(encoding="utf-8").rstrip()
    path.write_text(f"{current}\n\n[自动采纳的复盘建议]\n- {text}\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
