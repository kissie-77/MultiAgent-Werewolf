"""History support helpers for prompt evolution proposals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.evolution.prompt_patch import (
    LIST_REPLACE_KEYWORDS,
    normalize_rule_text,
)


def build_history_support(
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
            key = proposal_support_key(row)
            if key not in support:
                support[key] = {"support_count": 0, "run_dirs": []}
            support[key]["support_count"] += 1
            support[key]["run_dirs"].append(sibling.name)
    return support


def proposal_support_key(row: dict[str, Any]) -> tuple[str, str, str]:
    patch = row.get("suggested_patch") or {}
    target_field = str(patch.get("target_field") or "").strip()
    action = str(patch.get("action") or "").strip()
    text = normalize_rule_text(str(patch.get("text_zh") or ""))
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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
