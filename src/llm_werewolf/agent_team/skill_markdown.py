"""Shared helpers for Skill Markdown parsing and description rules."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
DESCRIPTION_PREFIXES = ("描述：", "描述:", "description:", "Description:")
DESCRIPTION_SUFFIX = "的情况下，使用该 skill"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse simple YAML-like frontmatter used by local Skill files."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text.strip()
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, text[match.end() :].strip()


def read_skill_markdown(path: Path) -> tuple[dict[str, str], str]:
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def render_frontmatter_markdown(meta: Mapping[str, object], body: str) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if value is not None and value != "":
            lines.append(f"{key}: {value}")
    lines.extend(["---", ""])
    if body.strip():
        lines.extend([body.strip(), ""])
    return "\n".join(lines)


def split_description_line(content: str) -> tuple[str, str]:
    lines = content.strip().splitlines()
    if not lines:
        return "", ""
    first = lines[0].strip()
    for prefix in DESCRIPTION_PREFIXES:
        if first.startswith(prefix):
            description = first[len(prefix) :].strip()
            return ensure_description_format(description), "\n".join(lines[1:]).strip()
    return "", content.strip()


def extract_description(content: str) -> str:
    description, body = split_description_line(content)
    if description:
        return description
    when_to_use = extract_when_to_use(body or content)
    if when_to_use:
        return ensure_description_format(when_to_use)
    source = body or content
    match = re.search(r"[。！？!?；;]", source)
    if match:
        candidate = source[: match.start()].strip()
    else:
        candidate = source.strip()[:30]
    return ensure_description_format(candidate)


def extract_when_to_use(content: str) -> str:
    """Extract the first useful line from a Skill Markdown '何时使用' section."""
    lines = content.strip().splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if in_section and stripped.startswith("#"):
            break
        if re.match(r"^#+\s*何时使用\s*$", stripped):
            in_section = True
            continue
        if in_section:
            collected.append(stripped)

    for line in collected:
        normalized = line.strip()
        if not normalized:
            continue
        normalized = re.sub(r"^[-*•\d.、)）\s]+", "", normalized).strip()
        if normalized:
            return normalized[:120]
    return ""


def ensure_description_format(text: str) -> str:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return f"通用对局经验{DESCRIPTION_SUFFIX}"
    if normalized.endswith(DESCRIPTION_SUFFIX):
        return normalized
    normalized = normalized.rstrip("。.!！")
    if normalized.endswith("的情况下"):
        return f"{normalized}，使用该 skill"
    return f"{normalized}{DESCRIPTION_SUFFIX}"


def strip_legacy_description_line(body: str) -> str:
    """Remove old leading description lines when '何时使用' already carries the trigger."""
    lines = body.strip().splitlines()
    if not lines:
        return ""
    first = lines[0].strip()
    if first.startswith(DESCRIPTION_PREFIXES) and re.search(r"^#+\s*何时使用\s*$", body, re.MULTILINE):
        return "\n".join(lines[1:]).strip()
    return body.strip()
