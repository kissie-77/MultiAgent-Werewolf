"""Prompt role-card patch helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

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


def apply_to_role_card(path: Path, patch: dict[str, Any], text: str) -> bool:
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
        current = _get_nested_value(data, target_field)
        if current is not None:
            _set_nested_value(data, target_field, text)
            _write_yaml(path, data)
            return True
        return False

    if action == "deprecate_rule" and target_field:
        parts = target_field.split(".")
        if len(parts) == 2 and parts[0] in ("core_principles", "forbidden_actions", "examples"):
            items = _ensure_list(data, parts[0])
            normalized_target = normalize_rule_text(parts[1])
            for idx, existing in enumerate(items):
                if normalize_rule_text(existing) == normalized_target:
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


def normalize_rule_text(text: str) -> str:
    return "".join(str(text).strip().lower().split())


def _ensure_list(data: dict[str, Any], key: str) -> list[str]:
    raw = data.get(key)
    if isinstance(raw, list):
        return raw
    data[key] = []
    return data[key]


def _replace_or_append_list_item(items: list[str], new_text: str, *, list_key: str) -> None:
    normalized_new = normalize_rule_text(new_text)
    if not normalized_new:
        return
    for idx, existing in enumerate(items):
        normalized_existing = normalize_rule_text(existing)
        if normalized_existing == normalized_new:
            items[idx] = new_text
            return
        if _is_same_rule_family(normalized_existing, normalized_new, list_key=list_key):
            items[idx] = new_text
            return
    items.append(new_text)


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


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
