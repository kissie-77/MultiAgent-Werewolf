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
from llm_werewolf.strategy.role_prompt_registry import (
    copy_role_prompt_package,
    register_role_prompt_search_root,
)
from llm_werewolf.strategy.role_version_manifest import (
    RoleVersionManifest,
    get_active_manifest,
    next_version_label,
    set_active_manifest,
)

PROMPT_VERSIONS_ROOT = Path("artifacts") / "prompt_versions"
DEFAULT_HISTORY_WINDOW = 5
SUPPORTED_KINDS = {
    "mvp_golden_quote",
    "mvp_strategy_highlight",
    "positive_persuasion",
    "bad_case_rule",
}
SUPPORTED_ACTIONS = {
    "append_guidance",
    "update_rule",
    "promote_quote_to_example",
    "add_forbidden_rule",
    "replace_rule",
    "deprecate_rule",
}

_POSITIVE_PROPOSAL_KINDS = frozenset({"mvp_golden_quote", "positive_persuasion"})


def _proposal_has_matched_elimination(row: dict[str, Any]) -> bool:
    evidence = row.get("evidence") or {}
    if not isinstance(evidence, dict):
        return False
    return bool(evidence.get("matched_elimination") or evidence.get("matched_round_elimination"))

LIST_REPLACE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "forbidden_actions": (
        "空白",
        "占位",
        "座位号",
        "极短",
        "空泛",
        "大家谨慎",
        "重复查验",
        "下毒",
        "毒药",
        "开枪",
        "枪口",
        "归票",
    ),
    "examples": (
        "归票",
        "回查",
        "发言",
        "查验",
        "下毒",
        "开枪",
        "落刀",
    ),
}


@dataclass(frozen=True)
class PromptEvolutionResult:
    base_prompt_version: str
    new_prompt_version: str
    new_version_dir: Path | None
    applied_count: int
    applied_path: Path
    diff_path: Path
    evidence_ledger_path: Path
    role_version_manifest: dict[str, Any] | None = None
    changed_prompt_roles: dict[str, dict[str, str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_prompt_version": self.base_prompt_version,
            "new_prompt_version": self.new_prompt_version,
            "new_version_dir": (
                str(self.new_version_dir) if self.new_version_dir is not None else None
            ),
            "applied_count": self.applied_count,
            "applied_path": str(self.applied_path),
            "diff_path": str(self.diff_path),
            "evidence_ledger_path": str(self.evidence_ledger_path),
            "role_version_manifest": self.role_version_manifest,
            "changed_prompt_roles": self.changed_prompt_roles,
        }


def evolve_prompt_from_run(
    run_dir: str | Path,
    *,
    base_prompt_version: str | None = None,
    role_version_manifest: RoleVersionManifest | None = None,
    output_root: str | Path = PROMPT_VERSIONS_ROOT,
    max_per_role: int = 2,
    min_confidence_score: float = 0.68,
    history_window: int = DEFAULT_HISTORY_WINDOW,
) -> PromptEvolutionResult:
    base = Path(run_dir)
    proposals_path = base / "prompt_proposals.json"
    output_base = Path(output_root)
    register_role_prompt_search_root(output_base)
    manifest = role_version_manifest or get_active_manifest()
    legacy_base = base_prompt_version or manifest.default_prompt_version
    proposals_payload = _read_json(proposals_path)
    history_support = _build_history_support(base, window=history_window)
    proposals, skipped_low_confidence = _select_proposals(
        proposals_payload,
        max_per_role=max_per_role,
        min_confidence_score=min_confidence_score,
        history_support=history_support,
    )

    applied_path = base / "applied_prompt_proposals.json"
    diff_path = base / "prompt_version_diff.json"
    evidence_ledger_path = base / "prompt_evidence_ledger.json"

    if not proposals:
        _write_json(
            applied_path,
            {
                "schema": "applied_prompt_proposals_v2",
                "base_prompt_version": legacy_base,
                "new_prompt_version": legacy_base,
                "applied_count": 0,
                "applied": [],
                "skipped_low_confidence": skipped_low_confidence,
                "skipped_reason": "no_applicable_prompt_proposals",
                "role_version_manifest": manifest.to_dict(),
            },
        )
        _write_json(
            diff_path,
            {
                "schema": "prompt_version_diff_v2",
                "base_prompt_version": legacy_base,
                "new_prompt_version": legacy_base,
                "changes": [],
                "changed_prompt_roles": {},
            },
        )
        _write_evidence_ledger(
            evidence_ledger_path,
            base_prompt_version=legacy_base,
            new_prompt_version=legacy_base,
            applied=[],
            skipped_low_confidence=skipped_low_confidence,
        )
        return PromptEvolutionResult(
            base_prompt_version=legacy_base,
            new_prompt_version=legacy_base,
            new_version_dir=None,
            applied_count=0,
            applied_path=applied_path,
            diff_path=diff_path,
            evidence_ledger_path=evidence_ledger_path,
            role_version_manifest=manifest.to_dict(),
            changed_prompt_roles={},
        )

    updated_manifest = manifest
    changes: list[dict[str, Any]] = []
    changed_roles: dict[str, dict[str, str]] = {}
    last_dir: Path | None = None
    grouped: dict[str, list[dict[str, Any]]] = {}
    for proposal in proposals:
        role_key = str(proposal.get("prompt_role_key") or "villager")
        grouped.setdefault(role_key, []).append(proposal)

    for role_key, role_proposals in grouped.items():
        base_version = updated_manifest.prompt_version_for(role_key)
        new_version = next_version_label(base_version)
        try:
            target_dir = copy_role_prompt_package(
                role_key,
                base_version,
                new_version,
                output_root=output_base,
            )
        except FileNotFoundError:
            continue
        role_yaml = target_dir / "role.yaml"
        for proposal in role_proposals:
            patch = proposal.get("suggested_patch") or {}
            if not isinstance(patch, dict):
                continue
            text = str(patch.get("text_zh") or "").strip()
            if not text:
                continue
            if _apply_to_role_card(role_yaml, patch, text):
                changes.append(
                    {
                        "proposal_id": proposal.get("proposal_id"),
                        "prompt_role_key": role_key,
                        "target_field": patch.get("target_field"),
                        "section": patch.get("section"),
                        "action": patch.get("action"),
                        "text_zh": text,
                        "prompt_version_before": base_version,
                        "prompt_version_after": new_version,
                    }
                )
        updated_manifest = updated_manifest.with_prompt_version(role_key, new_version)
        changed_roles[role_key] = {"before": base_version, "after": new_version}
        last_dir = target_dir

    set_active_manifest(updated_manifest)
    summary_version = updated_manifest.default_prompt_version

    _write_json(
        applied_path,
        {
            "schema": "applied_prompt_proposals_v2",
            "base_prompt_version": legacy_base,
            "new_prompt_version": summary_version,
            "applied_count": len(changes),
            "applied": proposals,
            "skipped_low_confidence": skipped_low_confidence,
            "role_version_manifest": updated_manifest.to_dict(),
            "changed_prompt_roles": changed_roles,
        },
    )
    _write_json(
        diff_path,
        {
            "schema": "prompt_version_diff_v2",
            "base_prompt_version": legacy_base,
            "new_prompt_version": summary_version,
            "changes": changes,
            "changed_prompt_roles": changed_roles,
        },
    )
    _write_evidence_ledger(
        evidence_ledger_path,
        base_prompt_version=legacy_base,
        new_prompt_version=summary_version,
        applied=proposals,
        skipped_low_confidence=skipped_low_confidence,
    )
    (base / "new_prompt_version.txt").write_text(summary_version, encoding="utf-8")
    return PromptEvolutionResult(
        base_prompt_version=legacy_base,
        new_prompt_version=summary_version,
        new_version_dir=last_dir,
        applied_count=len(changes),
        applied_path=applied_path,
        diff_path=diff_path,
        evidence_ledger_path=evidence_ledger_path,
        role_version_manifest=updated_manifest.to_dict(),
        changed_prompt_roles=changed_roles,
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _judge_proposal(
    row: dict[str, Any],
    *,
    effective_confidence_score: float,
    support_count: int,
    min_confidence_score: float,
) -> dict[str, Any]:
    """对单条提案做多维度采纳判定，返回 judgment 字典。

    采纳规则（满足任意一条即通过）：
    1. 置信度达标 + 历史支持 >= 2 次
    2. 来自 bad_case_rule 且置信度达标
    3. 置信度 >= 0.85（高置信度直接通过）
    """
    kind = str(row.get("kind") or "")
    criteria_met: list[str] = []
    criteria_failed: list[str] = []

    # 条件 1：置信度达标
    if effective_confidence_score >= min_confidence_score:
        criteria_met.append("confidence达标")
    else:
        criteria_failed.append(f"confidence不足({effective_confidence_score:.2f}<{min_confidence_score})")

    # 条件 2：历史支持次数达标（>=2 次跨 run 出现）
    if support_count >= 2:
        criteria_met.append(f"历史支持({support_count}次)")
    else:
        criteria_failed.append(f"历史支持不足({support_count}次)")

    # 条件 3：来自 bad case 严重错误修复
    if kind == "bad_case_rule":
        criteria_met.append("bad_case修复")
    else:
        criteria_failed.append("非bad_case")

    if kind in _POSITIVE_PROPOSAL_KINDS:
        if _proposal_has_matched_elimination(row):
            criteria_met.append("matched放逐")
        else:
            criteria_failed.append("未matched放逐")

    # 采纳规则
    confidence_ok = effective_confidence_score >= min_confidence_score
    high_confidence = effective_confidence_score >= 0.85
    has_history = support_count >= 1
    is_bad_case = kind == "bad_case_rule"
    positive_ok = kind not in _POSITIVE_PROPOSAL_KINDS or _proposal_has_matched_elimination(row)

    accepted = positive_ok and (
        (confidence_ok and has_history)     # 规则 1：置信度 + 历史支持
        or (is_bad_case and confidence_ok)   # 规则 2：bad case + 置信度
        or high_confidence                   # 规则 3：高置信度直接通过
    )

    return {
        "accepted": accepted,
        "criteria_met": criteria_met,
        "criteria_failed": criteria_failed,
        "verdict": "采纳" if accepted else "拒绝",
    }


def _select_proposals(
    payload: dict[str, Any],
    *,
    max_per_role: int,
    min_confidence_score: float,
    history_support: dict[tuple[str, str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    skipped_low_confidence: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    seen: set[tuple[str, str, str, str]] = set()
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
        target_field = str(patch.get("target_field") or "").strip()
        role_key = str(row.get("prompt_role_key") or "global")
        confidence_score = float(row.get("confidence_score") or 0.0)
        support_key = _proposal_support_key(row)
        support = history_support.get(support_key, {})
        support_count = int(support.get("support_count") or 0)
        historical_bonus = min(0.2, support_count * 0.06)
        effective_confidence_score = min(1.0, round(confidence_score + historical_bonus, 3))
        row["history_support_count"] = support_count
        row["effective_confidence_score"] = effective_confidence_score
        if not text or not target:
            continue

        # 显式采纳判定
        judgment = _judge_proposal(
            row,
            effective_confidence_score=effective_confidence_score,
            support_count=support_count,
            min_confidence_score=min_confidence_score,
        )
        row["judgment"] = judgment

        if not judgment["accepted"]:
            skipped_low_confidence.append(
                {
                    "proposal_id": row.get("proposal_id"),
                    "prompt_role_key": role_key,
                    "confidence_score": confidence_score,
                    "effective_confidence_score": effective_confidence_score,
                    "history_support_count": support_count,
                    "judgment": judgment,
                    "reason": "未通过采纳判定",
                }
            )
            continue
        if counts.get(role_key, 0) >= max_per_role:
            continue
        key = (target, section, target_field, text)
        if key in seen:
            continue
        seen.add(key)
        counts[role_key] = counts.get(role_key, 0) + 1
        selected.append(row)
    return selected, skipped_low_confidence


def _build_history_support(
    run_dir: Path,
    *,
    window: int,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    parent = run_dir.parent
    if not parent.is_dir():
        return {}
    siblings = sorted(
        [path for path in parent.iterdir() if path.is_dir() and path != run_dir],
        key=lambda path: path.name,
    )[-window:]
    support: dict[tuple[str, str, str], dict[str, Any]] = {}
    for sibling in siblings:
        payload = _read_json(sibling / "prompt_proposals.json")
        for row in payload.get("proposals") or []:
            if not isinstance(row, dict):
                continue
            key = _proposal_support_key(row)
            if key not in support:
                support[key] = {"support_count": 0, "run_dirs": []}
            support[key]["support_count"] += 1
            support[key]["run_dirs"].append(sibling.name)
    return support


def _proposal_support_key(row: dict[str, Any]) -> tuple[str, str, str]:
    patch = row.get("suggested_patch") or {}
    target_field = str(patch.get("target_field") or "").strip()
    action = str(patch.get("action") or "").strip()
    text = _normalize_rule_text(str(patch.get("text_zh") or ""))
    return (
        str(row.get("prompt_role_key") or "global"),
        target_field or action,
        _support_topic_key(text),
    )


def _support_topic_key(text: str) -> str:
    if not text:
        return ""
    compact = text[:24]
    for keyword_group in LIST_REPLACE_KEYWORDS.values():
        for keyword in keyword_group:
            if keyword and keyword in text:
                return keyword
    return compact


def _build_next_prompt_version(base_prompt_version: str, run_name: str) -> str:
    clean_run_name = "".join(
        ch if ch.isalnum() else "_" for ch in run_name.lower()
    ).strip("_")
    return f"{base_prompt_version}_{clean_run_name}_prompt"


def _copy_prompt_version(
    base_prompt_version: str,
    new_prompt_version: str,
    target_dir: Path,
) -> None:
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
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

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
    variables_path.write_text(
        yaml.safe_dump(variables, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _apply_proposals(
    version_dir: Path,
    new_prompt_version: str,
    proposals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    variables = yaml.safe_load((version_dir / "variables.yaml").read_text(encoding="utf-8")) or {}
    specs = variables.get("variables") or {}
    changes: list[dict[str, Any]] = []
    for proposal in proposals:
        target = _target_for_new_version(
            str(proposal.get("target_variable") or ""),
            new_prompt_version,
        )
        patch = proposal.get("suggested_patch") or {}
        if not isinstance(patch, dict):
            continue
        text = str(patch.get("text_zh") or "").strip()
        if not text:
            continue
        spec = _resolve_target_spec(specs, target)
        if not isinstance(spec, dict):
            continue
        target_path = version_dir / str(spec.get("file") or "")
        if spec.get("kind") == "role_card":
            applied = _apply_to_role_card(target_path, patch, text)
        else:
            applied = _append_to_text_file(target_path, text)
        if not applied:
            continue
        changes.append(
            {
                "proposal_id": proposal.get("proposal_id"),
                "target_variable": target,
                "target_field": patch.get("target_field"),
                "section": patch.get("section"),
                "action": patch.get("action"),
                "text_zh": text,
            }
        )
    return changes


def _resolve_target_spec(specs: dict[str, Any], target: str) -> dict[str, Any] | None:
    spec = specs.get(target)
    if isinstance(spec, dict):
        return spec
    role_target = ".".join(target.split(".")[:3])
    role_spec = specs.get(role_target)
    if isinstance(role_spec, dict):
        return role_spec
    return None


def _target_for_new_version(target_variable: str, new_prompt_version: str) -> str:
    parts = target_variable.split(".", 1)
    if len(parts) != 2:
        return target_variable
    return f"{new_prompt_version}.{parts[1]}"


def _apply_to_role_card(path: Path, patch: dict[str, Any], text: str) -> bool:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    action = str(patch.get("action") or "")
    target_field = str(patch.get("target_field") or "").strip()

    if action == "promote_quote_to_example":
        examples = _ensure_list(data, "examples")
        _replace_or_append_list_item(examples, text, list_key="examples")
        _write_yaml(path, data)
        return True

    if action == "add_forbidden_rule":
        forbidden_actions = _ensure_list(data, "forbidden_actions")
        _replace_or_append_list_item(
            forbidden_actions,
            text,
            list_key="forbidden_actions",
        )
        _write_yaml(path, data)
        return True

    if action == "update_rule" and target_field:
        _set_nested_value(data, target_field, text)
        _write_yaml(path, data)
        return True

    if action == "replace_rule" and target_field:
        # 替换 core_principles / phase_strategies / forbidden_actions 中的同类规则
        current = _get_nested_value(data, target_field)
        if current is not None:
            _set_nested_value(data, target_field, text)
            _write_yaml(path, data)
            return True
        return False

    if action == "deprecate_rule" and target_field:
        # 从列表字段中移除匹配的规则
        parts = target_field.split(".")
        if len(parts) == 2 and parts[0] in ("core_principles", "forbidden_actions", "examples"):
            items = _ensure_list(data, parts[0])
            normalized_target = _normalize_rule_text(parts[1])
            for idx, existing in enumerate(items):
                if _normalize_rule_text(existing) == normalized_target:
                    items.pop(idx)
                    _write_yaml(path, data)
                    return True
        return False

    if action == "append_guidance":
        suggestion = str(data.get("suggestion") or "").strip()
        marker = "\n\n[自动采纳的复盘建议]\n- "
        data["suggestion"] = f"{suggestion}{marker}{text}" if suggestion else text
        _write_yaml(path, data)
        return True

    return False


def _ensure_list(data: dict[str, Any], key: str) -> list[str]:
    raw = data.get(key)
    if isinstance(raw, list):
        return raw
    data[key] = []
    return data[key]


def _replace_or_append_list_item(items: list[str], new_text: str, *, list_key: str) -> None:
    normalized_new = _normalize_rule_text(new_text)
    if not normalized_new:
        return
    for idx, existing in enumerate(items):
        normalized_existing = _normalize_rule_text(existing)
        if normalized_existing == normalized_new:
            items[idx] = new_text
            return
        if _is_same_rule_family(normalized_existing, normalized_new, list_key=list_key):
            items[idx] = new_text
            return
    items.append(new_text)


def _normalize_rule_text(text: str) -> str:
    return "".join(str(text).strip().lower().split())


def _is_same_rule_family(existing: str, new: str, *, list_key: str) -> bool:
    if not existing or not new:
        return False
    if existing[:12] == new[:12]:
        return True
    keywords = LIST_REPLACE_KEYWORDS.get(list_key, ())
    shared = [keyword for keyword in keywords if keyword in existing and keyword in new]
    return len(shared) >= 1


def _get_nested_value(data: dict[str, Any], path: str) -> Any:
    parts = [part for part in path.split(".") if part]
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_nested_value(data: dict[str, Any], path: str, value: str) -> None:
    parts = [part for part in path.split(".") if part]
    current: dict[str, Any] = data
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _append_to_text_file(path: Path, text: str) -> bool:
    current = path.read_text(encoding="utf-8").rstrip()
    path.write_text(
        f"{current}\n\n[自动采纳的复盘建议]\n- {text}\n",
        encoding="utf-8",
    )
    return True


def _write_evidence_ledger(
    path: Path,
    *,
    base_prompt_version: str,
    new_prompt_version: str,
    applied: list[dict[str, Any]],
    skipped_low_confidence: list[dict[str, Any]],
) -> None:
    entries: list[dict[str, Any]] = []
    for row in applied:
        patch = row.get("suggested_patch") or {}
        entries.append(
            {
                "proposal_id": row.get("proposal_id"),
                "status": "applied",
                "prompt_role_key": row.get("prompt_role_key"),
                "kind": row.get("kind"),
                "target_field": patch.get("target_field"),
                "action": patch.get("action"),
                "confidence_score": row.get("confidence_score"),
                "history_support_count": row.get("history_support_count", 0),
                "effective_confidence_score": row.get("effective_confidence_score"),
                "evidence_scope": row.get("evidence_scope"),
                "text_zh": patch.get("text_zh"),
            }
        )
    for row in skipped_low_confidence:
        entries.append(
            {
                "proposal_id": row.get("proposal_id"),
                "status": "skipped_low_confidence",
                "prompt_role_key": row.get("prompt_role_key"),
                "confidence_score": row.get("confidence_score"),
                "history_support_count": row.get("history_support_count", 0),
                "effective_confidence_score": row.get("effective_confidence_score"),
                "reason": row.get("reason"),
            }
        )
    _write_json(
        path,
        {
            "schema": "prompt_evidence_ledger_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "base_prompt_version": base_prompt_version,
            "new_prompt_version": new_prompt_version,
            "entry_count": len(entries),
            "entries": entries,
        },
    )


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
