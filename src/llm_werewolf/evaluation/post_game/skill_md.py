"""Skill 卡片 Markdown 序列化（含 YAML frontmatter）。"""

from __future__ import annotations

from typing import Any


def render_skill_markdown(skill: dict[str, Any]) -> str:
    """将 role_skills.json 中的单条 skill 渲染为 Markdown 文件正文。"""
    card = skill.get("skill_card") or {}
    evidence = skill.get("evidence") or {}
    quality = skill.get("quality_gate") or {}

    frontmatter = {
        "skill_id": skill.get("skill_id", ""),
        "prompt_role_key": skill.get("prompt_role_key", ""),
        "status": skill.get("status", "draft"),
        "source_run": skill.get("source_run", ""),
        "source_player_id": skill.get("source_player_id", ""),
        "camp": skill.get("camp", ""),
        "quality_passed": quality.get("passed", False),
    }
    lines = ["---"]
    for key, value in frontmatter.items():
        if value is not None and value != "":
            lines.append(f"{key}: {value}")
    lines.extend(["---", ""])

    title = card.get("title_zh") or skill.get("skill_id") or "未命名 Skill"
    lines.append(f"# {title}")
    lines.append("")

    if skill.get("rationale"):
        lines.append("## 提取依据")
        lines.append(str(skill["rationale"]))
        lines.append("")

    if card.get("background"):
        lines.append("## 局面背景")
        lines.append(str(card["background"]))
        lines.append("")

    scenario = card.get("applicable_scenario") or card.get("when_to_use")
    if scenario:
        lines.append("## 适用场景")
        lines.append(str(scenario))
        lines.append("")

    citations = skill.get("citations") or []
    if citations:
        lines.append("## 引用来源")
        for ref in citations:
            label = ref.get("label") or ref.get("type") or "引用"
            path = ref.get("path", "")
            lines.append(f"- **{label}**：`{path}`")
            if ref.get("quote"):
                lines.append(f"  > {ref['quote'][:200]}")
        lines.append("")

    if card.get("public_behavior"):
        lines.append("## 公开行为")
        lines.append(str(card["public_behavior"]))
        lines.append("")

    if card.get("avoid"):
        lines.append("## 避免")
        lines.append(str(card["avoid"]))
        lines.append("")

    excerpt = evidence.get("public_speech_excerpt")
    if excerpt:
        lines.append("## 本局发言摘录")
        lines.append(f"> {excerpt}")
        lines.append("")

    scores = evidence.get("scores")
    if scores:
        lines.append("## 评分")
        for key, value in scores.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
