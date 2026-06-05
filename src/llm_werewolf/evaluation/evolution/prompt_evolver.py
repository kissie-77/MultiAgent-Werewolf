from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from llm_werewolf.evaluation.evolution.prompt_history import (
    build_history_support,
    proposal_support_key,
)
from llm_werewolf.evaluation.evolution.prompt_patch import apply_to_role_card

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
    history_support = build_history_support(base, window=history_window)
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
            if apply_to_role_card(role_yaml, patch, text):
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
        support_key = proposal_support_key(row)
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
