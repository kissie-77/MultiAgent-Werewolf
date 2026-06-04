"""从 `agent_team/skills/<身份>/<版本>/` 加载 Skill Markdown，供系统 Prompt 引用。"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from pathlib import Path
from functools import lru_cache

from llm_werewolf.agent_team.skill_support.skill_markdown import (
    ensure_description_format,
    extract_description,
    extract_markdown_section,
    parse_frontmatter,
)
from llm_werewolf.strategy.belief_format import summarize_belief_pattern
from llm_werewolf.strategy.role_version_manifest import get_active_manifest

if TYPE_CHECKING:
    from llm_werewolf.strategy.belief_state import BeliefState

_SKILLS_DIR_NAME = "skills"
_UNTRUSTED_SOURCE_RUN_MARKERS = (
    "/pytest-of-",
    "/private/",
    "/tmp/",
    "\\pytest-of-",
    "artifacts/runs/",
)


def agent_skills_root() -> Path:
    return Path(__file__).resolve().parent.parent / _SKILLS_DIR_NAME


def is_trusted_source_run(source_run: str) -> bool:
    """Reject pytest/tmp paths when auto-joining skills into the shared library."""
    normalized = source_run.replace("\\", "/").strip().lower()
    if not normalized:
        return False
    return not any(marker in normalized for marker in _UNTRUSTED_SOURCE_RUN_MARKERS)


def resolve_skill_version(role_key: str, skill_version: str | None = None) -> str:
    if skill_version is not None and skill_version.strip():
        return skill_version.strip()
    return get_active_manifest().skill_version_for(role_key)


def role_skill_version_dir(role_key: str, skill_version: str | None = None) -> Path:
    version = resolve_skill_version(role_key, skill_version)
    return agent_skills_root() / role_key / version


def list_skill_versions(role_key: str) -> tuple[str, ...]:
    from llm_werewolf.strategy.role_version_manifest import list_skill_versions as _list_versions

    return _list_versions(role_key)


def resolve_latest_skill_version(role_key: str, *, fallback: str = "v1") -> str:
    from llm_werewolf.strategy.role_version_manifest import pick_latest_version

    return pick_latest_version(list_skill_versions(role_key), fallback=fallback)


def next_skill_version(role_key: str, current: str | None = None) -> str:
    from llm_werewolf.strategy.role_version_manifest import next_version_label

    base = current or resolve_skill_version(role_key)
    candidate = next_version_label(base)
    existing = set(list_skill_versions(role_key))
    while candidate in existing:
        candidate = next_version_label(candidate)
    return candidate


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    return parse_frontmatter(text)


def _load_skill_file(path: Path) -> dict[str, str | float] | None:
    if not path.is_file() or path.suffix.lower() != ".md":
        return None
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    status = meta.get("status", "draft")
    if status == "skipped":
        return None
    when_to_use = meta.get("when_to_use", "").strip()
    if when_to_use:
        description = ensure_description_format(when_to_use)
    else:
        description = extract_description(body)
    try:
        weight = float(meta.get("weight", 1.0))
    except (ValueError, TypeError):
        weight = 1.0
    return {
        "skill_id": meta.get("skill_id", path.stem),
        "status": status,
        "weight": weight,
        "description": description,
        "body": body.strip(),
        "belief_pattern": parse_skill_belief_pattern(body, meta),
        "belief_signals": parse_skill_belief_signals(meta),
        "path": str(path),
        "skill_version": path.parent.name,
    }


@lru_cache(maxsize=32)
def list_role_skill_files(prompt_role_key: str, skill_version: str | None = None) -> tuple[Path, ...]:
    role_dir = role_skill_version_dir(prompt_role_key, skill_version)
    if not role_dir.is_dir():
        return ()
    return tuple(sorted(role_dir.glob("*.md")))


def load_role_skills(
    prompt_role_key: str,
    *,
    include_draft: bool = False,
    max_skills: int = 5,
    skill_version: str | None = None,
) -> list[dict[str, str | float]]:
    """加载某身份指定版本目录下的 Skill MD（默认仅 active），按 weight 降序。"""
    loaded: list[dict[str, str | float]] = []
    for path in list_role_skill_files(prompt_role_key, skill_version):
        item = _load_skill_file(path)
        if item is None:
            continue
        if item["status"] == "deprecated":
            continue
        if not include_draft and item["status"] != "active":
            continue
        loaded.append(item)
    loaded.sort(key=lambda s: s.get("weight", 1.0), reverse=True)
    return loaded[:max_skills]


def format_role_skills_section(
    prompt_role_key: str,
    *,
    include_draft: bool = False,
    max_skills: int = 5,
    skill_version: str | None = None,
) -> str:
    skills = load_role_skills(
        prompt_role_key,
        include_draft=include_draft,
        max_skills=max_skills,
        skill_version=skill_version,
    )
    if not skills:
        return ""
    version = resolve_skill_version(prompt_role_key, skill_version)
    parts = [
        f"【对局经验 Skill 卡片（{prompt_role_key}@{version}）— 可参考，须符合当前局面与信息边界】"
    ]
    for idx, skill in enumerate(skills, start=1):
        parts.append(f"\n### Skill {idx}（{skill['skill_id']}）\n{skill['description']}")
    return "\n".join(parts)


def load_role_skills_text(
    prompt_role_key: str,
    *,
    include_draft: bool = False,
    max_skills: int = 5,
    skill_version: str | None = None,
) -> str:
    return format_role_skills_section(
        prompt_role_key,
        include_draft=include_draft,
        max_skills=max_skills,
        skill_version=skill_version,
    )


def copy_skills_to_new_version(
    role_key: str,
    *,
    base_version: str | None = None,
    new_version: str | None = None,
) -> str:
    """Copy all skill MD files from base_version to new_version folder."""
    base = base_version or resolve_skill_version(role_key)
    target_version = new_version or next_skill_version(role_key, base)
    source_dir = role_skill_version_dir(role_key, base)
    target_dir = role_skill_version_dir(role_key, target_version)
    target_dir.mkdir(parents=True, exist_ok=True)
    if source_dir.is_dir():
        for path in source_dir.glob("*.md"):
            (target_dir / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    list_role_skill_files.cache_clear()
    return target_version


_PATTERN_HINTS: dict[str, tuple[str, ...]] = {
    "dispersed": ("狼信分散", "怀疑焦点分散", "带节奏", "收束票型"),
    "split_focus": ("双怀疑", "焦点分散", "择一归票", "拆局"),
    "concentrated": ("狼信极高", "单一目标", "顺势推动"),
    "converging": ("怀疑收敛", "强化归票", "避免分票"),
    "undecided": ("信息不足", "观望", "未收敛"),
    "self_exposed": ("洗清自身", "被他人高怀疑", "B2"),
    "mixed": ("结合公开信息", "票型缺口"),
}

_PATTERN_LINE = re.compile(r"分布模式[：:]\s*(\w+)")


def parse_skill_belief_pattern(body: str, meta: dict[str, str] | None = None) -> str:
    meta = meta or {}
    raw = str(meta.get("belief_pattern", "")).strip()
    if raw:
        return raw
    if not body.strip():
        return ""
    match = _PATTERN_LINE.search(body)
    if match:
        return match.group(1).strip()
    return ""


def parse_skill_belief_signals(meta: dict[str, str] | None = None) -> frozenset[str]:
    meta = meta or {}
    raw = str(meta.get("belief_signals", "")).strip()
    if not raw:
        return frozenset()
    return frozenset(item.strip() for item in raw.split(",") if item.strip())


def summarize_belief_state(state: BeliefState | None):
    return summarize_belief_pattern(state)


def _score_skill_for_belief(
    skill: dict[str, str | float],
    *,
    active_signals: frozenset[str],
    pattern: str,
    when_clause: str,
) -> float:
    skill_signals = skill.get("belief_signals")
    if not isinstance(skill_signals, frozenset):
        skill_signals = parse_skill_belief_signals(
            {"belief_signals": str(skill.get("belief_signals", ""))}
        )

    if skill_signals:
        if not skill_signals.issubset(active_signals):
            return 0.0
        score = 100.0 + 20.0 * len(skill_signals)
        score += float(skill.get("weight", 1.0)) * 5.0
        return score

    skill_pattern = str(skill.get("belief_pattern", "")).strip()
    description = str(skill.get("description", ""))
    body = str(skill.get("body", ""))
    text = f"{description}\n{body}"

    score = 0.0
    if skill_pattern:
        if skill_pattern != pattern:
            return 0.0
        score += 100.0

    hints = _PATTERN_HINTS.get(pattern, ())
    if hints and any(hint in text for hint in hints):
        score += 40.0
    if when_clause and hints and any(hint in when_clause for hint in hints):
        score += 20.0

    if not skill_pattern and score == 0.0:
        return 0.0

    score += float(skill.get("weight", 1.0)) * 5.0
    return score


def select_skills_for_belief(
    skills: list[dict[str, str | float]],
    state: BeliefState | None,
    *,
    top_k: int = 3,
) -> tuple[list[dict[str, str | float]], str | None, frozenset[str]]:
    summary = summarize_belief_state(state)
    if summary is None or not skills:
        return [], None, frozenset()

    pattern = summary.pattern
    when_clause = summary.when_clause
    active_signals = summary.signals
    scored: list[tuple[float, dict[str, str | float]]] = []
    for skill in skills:
        score = _score_skill_for_belief(
            skill,
            active_signals=active_signals,
            pattern=pattern,
            when_clause=when_clause,
        )
        if score > 0:
            scored.append((score, skill))

    scored.sort(
        key=lambda item: (
            -item[0],
            -float(item[1].get("weight", 1.0)),
            str(item[1].get("skill_id", "")),
        )
    )
    return [skill for _, skill in scored[:top_k]], pattern, active_signals


def format_belief_skill_context(
    skills: list[dict[str, str | float]],
    *,
    pattern: str | None = None,
    when_clause: str | None = None,
    active_signals: frozenset[str] | None = None,
    signal_descriptions: tuple[str, ...] | None = None,
) -> str:
    if not skills:
        return ""

    lines = ["【信念匹配的对局经验 · 仅供参考】"]
    if active_signals:
        lines.append(f"当前触发信号：{', '.join(sorted(active_signals))}")
    if signal_descriptions:
        lines.append("信号说明：" + "；".join(signal_descriptions))
    if pattern:
        lines.append(f"当前信念模式：{pattern}")
    if when_clause:
        lines.append(f"局面摘要：{when_clause}")
    lines.append("须结合当前局面与信息边界使用，不可机械套用历史号码或座位。")
    lines.append("")

    for skill in skills:
        skill_id = str(skill.get("skill_id", ""))
        description = str(skill.get("description", ""))
        body = str(skill.get("body", ""))
        behavior = extract_markdown_section(body, "公开行为")
        avoid = extract_markdown_section(body, "避免")

        lines.append(f"### {skill_id}")
        lines.append(description)
        if behavior:
            lines.append(f"公开行为：{behavior}")
        if avoid:
            lines.append(f"避免：{avoid}")
        lines.append("")

    return "\n".join(lines).strip()


def refresh_belief_skill_context(
    role_key: str,
    state: BeliefState | None,
    *,
    skill_version: str | None = None,
    pool_size: int = 12,
    top_k: int = 3,
) -> tuple[str, list[str]]:
    """Match skills to belief state; return formatted context and matched skill ids."""
    pool = load_role_skills(role_key, max_skills=pool_size, skill_version=skill_version)
    selected, pattern, active_signals = select_skills_for_belief(pool, state, top_k=top_k)
    summary = summarize_belief_state(state)
    context = format_belief_skill_context(
        selected,
        pattern=pattern,
        when_clause=summary.when_clause if summary else None,
        active_signals=active_signals,
        signal_descriptions=summary.signal_descriptions if summary else None,
    )
    skill_ids = [str(skill.get("skill_id", "")) for skill in selected if skill.get("skill_id")]
    return context, skill_ids
