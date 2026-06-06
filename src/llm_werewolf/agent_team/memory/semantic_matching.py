"""Pure text matching helpers for semantic memory cards."""

from __future__ import annotations

from difflib import SequenceMatcher
from collections import defaultdict


def normalize_content(content: str) -> str:
    return " ".join(content.strip().split())


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_content(left), normalize_content(right)).ratio()


def merge_card_contents(base: str, incoming: str) -> str:
    if normalize_content(base) == normalize_content(incoming):
        return base
    if incoming in base:
        return base
    return f"{base}\n\n{incoming}"


def deduplicate_candidates(candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for candidate in candidates:
        normalized = normalize_content(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(candidate.strip())
    return deduped


def merge_reflections(candidates: list[str]) -> list[str]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        prefix = candidate.split("：", 1)[0] if "：" in candidate else candidate
        grouped[prefix].append(candidate)

    merged: list[str] = []
    for prefix, items in grouped.items():
        if len(items) == 1:
            merged.append(items[0])
            continue
        suffixes = []
        for item in items:
            suffixes.append(item.split("：", 1)[1] if "：" in item else item)
        merged.append(f"{prefix}：" + "；".join(dict.fromkeys(suffixes)))
    return merged
