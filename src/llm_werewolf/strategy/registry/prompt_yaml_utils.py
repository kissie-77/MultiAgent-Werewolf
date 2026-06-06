"""Shared YAML helpers for role / phase prompt packages."""

from __future__ import annotations

from typing import Any


def coerce_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    text = str(value).strip()
    return [text] if text else []


def coerce_text_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key, item in value.items():
        text = str(item).strip()
        if text:
            out[str(key)] = text
    return out


def render_legacy_suggestion(data: dict[str, Any]) -> str:
    suggestion = str(data.get("suggestion", "")).strip()
    if suggestion:
        return suggestion

    sections: list[str] = []
    core_principles = coerce_text_list(data.get("core_principles"))
    if core_principles:
        sections.append("长期规则：")
        sections.extend(f"- {item}" for item in core_principles)

    phase_strategies = coerce_text_dict(data.get("phase_strategies"))
    if phase_strategies:
        sections.append("阶段策略：")
        for phase_name, rule in phase_strategies.items():
            sections.append(f"- {phase_name}: {rule}")

    forbidden_actions = coerce_text_list(data.get("forbidden_actions"))
    if forbidden_actions:
        sections.append("禁止项：")
        sections.extend(f"- {item}" for item in forbidden_actions)

    examples = coerce_text_list(data.get("examples"))
    if examples:
        sections.append("示例：")
        sections.extend(f"- {item}" for item in examples)

    return "\n".join(sections).strip()
