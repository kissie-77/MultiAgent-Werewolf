"""从 agent_team/skills/<身份>/ 加载 Skill Markdown，供系统 Prompt 引用。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_SKILLS_DIR_NAME = "skills"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def agent_skills_root() -> Path:
    return Path(__file__).resolve().parent / _SKILLS_DIR_NAME


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text.strip()
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    body = text[match.end() :].strip()
    return meta, body


def _load_skill_file(path: Path) -> dict[str, str] | None:
    if not path.is_file() or path.suffix.lower() != ".md":
        return None
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    status = meta.get("status", "draft")
    if status == "skipped":
        return None
    return {
        "skill_id": meta.get("skill_id", path.stem),
        "status": status,
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
) -> list[dict[str, str]]:
    """加载某身份目录下的 Skill MD（默认含 draft）。"""
    loaded: list[dict[str, str]] = []
    for path in list_role_skill_files(prompt_role_key):
        item = _load_skill_file(path)
        if item is None:
            continue
        if not include_draft and item["status"] == "draft":
            continue
        loaded.append(item)
        if len(loaded) >= max_skills:
            break
    return loaded


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
