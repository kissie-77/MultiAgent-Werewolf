"""从 `agent_team/skills/<身份>/` 加载 Skill Markdown，供系统 Prompt 引用。"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from llm_werewolf.agent_team.skill_support.skill_markdown import (
    extract_description,
    parse_frontmatter,
    strip_legacy_description_line,
)

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


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    return parse_frontmatter(text)



def _load_skill_file(path: Path) -> dict[str, str | float] | None:
    if not path.is_file() or path.suffix.lower() != ".md":
        return None
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    body = strip_legacy_description_line(body)
    status = meta.get("status", "draft")
    if status == "skipped":
        return None
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
        "path": str(path),
    }


@lru_cache(maxsize=16)
def list_role_skill_files(prompt_role_key: str) -> tuple[Path, ...]:
    role_dir = agent_skills_root() / prompt_role_key
    if not role_dir.is_dir():
        return ()
    return tuple(sorted(role_dir.glob("*.md")))


def load_role_skills(
    prompt_role_key: str, *, include_draft: bool = False, max_skills: int = 5
) -> list[dict[str, str | float]]:
    """加载某身份目录下的 Skill MD（默认仅 active），按 weight 降序。"""
    loaded: list[dict[str, str | float]] = []
    for path in list_role_skill_files(prompt_role_key):
        item = _load_skill_file(path)
        if item is None:
            continue
        if not include_draft and item["status"] == "draft":
            continue
        loaded.append(item)
    loaded.sort(key=lambda s: s.get("weight", 1.0), reverse=True)
    return loaded[:max_skills]


def format_role_skills_section(
    prompt_role_key: str, *, include_draft: bool = False, max_skills: int = 5
) -> str:
    """将 Skill 卡片格式化为可追加到系统 Prompt 的文本块。"""
    skills = load_role_skills(prompt_role_key, include_draft=include_draft, max_skills=max_skills)
    if not skills:
        return ""
    parts = ["【对局经验 Skill 卡片 — 可参考，须符合当前局面与信息边界】"]
    for idx, skill in enumerate(skills, start=1):
        parts.append(f"\n### Skill {idx}（{skill['skill_id']}）\n{skill['description']}")
    return "\n".join(parts)


def load_role_skills_text(
    prompt_role_key: str, *, include_draft: bool = False, max_skills: int = 5
) -> str:
    """供 factory / Agent 调用的薄封装。"""
    return format_role_skills_section(
        prompt_role_key, include_draft=include_draft, max_skills=max_skills
    )
