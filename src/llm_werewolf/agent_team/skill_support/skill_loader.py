"""从 agent_team/skills/<身份>/ 加载 Skill Markdown，供系统 Prompt 引用。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from llm_werewolf.agent_team.skill_support.skill_markdown import (
    parse_frontmatter,
    strip_legacy_description_line,
)

_SKILLS_DIR_NAME = "skills"


def agent_skills_root() -> Path:
    return Path(__file__).resolve().parent / _SKILLS_DIR_NAME


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    return parse_frontmatter(text)


def _strip_legacy_description_line(body: str) -> str:
    """兼容旧写入格式：标准 Skill MD 已用“何时使用”承载触发描述。"""
    return strip_legacy_description_line(body)


def _load_skill_file(path: Path) -> dict[str, str | float] | None:
    if not path.is_file() or path.suffix.lower() != ".md":
        return None
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    body = _strip_legacy_description_line(body)
    status = meta.get("status", "draft")
    if status == "skipped":
        return None
    try:
        weight = float(meta.get("weight", 1.0))
    except (ValueError, TypeError):
        weight = 1.0
    return {
        "skill_id": meta.get("skill_id", path.stem),
        "status": status,
        "weight": weight,
        "body": body,
        "path": str(path),
    }


@lru_cache(maxsize=16)
def list_role_skill_files(prompt_role_key: str) -> tuple[Path, ...]:
    role_dir = agent_skills_root() / prompt_role_key
    if not role_dir.is_dir():
        return ()
    return tuple(sorted(role_dir.glob("*.md")))


def load_role_skills(
    prompt_role_key: str,
    *,
    include_draft: bool = True,
    max_skills: int = 5,
) -> list[dict[str, str | float]]:
    """加载某身份目录下的 Skill MD（默认含 draft），按 weight 降序。"""
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
    prompt_role_key: str,
    *,
    include_draft: bool = True,
    max_skills: int = 5,
) -> str:
    """将 Skill 卡片格式化为可追加到系统 Prompt 的文本块。"""
    skills = load_role_skills(
        prompt_role_key,
        include_draft=include_draft,
        max_skills=max_skills,
    )
    if not skills:
        return ""
    parts = ["【对局经验 Skill 卡片 — 可参考，须符合当前局面与信息边界】"]
    for idx, skill in enumerate(skills, start=1):
        parts.append(f"\n### Skill {idx}（{skill['skill_id']}）\n{skill['body']}")
    return "\n".join(parts)


def load_role_skills_text(
    prompt_role_key: str,
    *,
    include_draft: bool = True,
    max_skills: int = 5,
) -> str:
    """供 PromptManager / Agent 调用的薄封装。"""
    return format_role_skills_section(
        prompt_role_key,
        include_draft=include_draft,
        max_skills=max_skills,
    )
