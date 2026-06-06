"""组装 LLM 资产提取用户 Prompt。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from llm_werewolf.evaluation.post_game.skill_generation.skill_belief_support import (
    format_belief_excerpts_for_prompt,
)
from llm_werewolf.evaluation.registry.post_game_prompt_registry import (
    AssetsPromptBundle,
    render_template,
)

if TYPE_CHECKING:
    from llm_werewolf.evaluation.post_game.run_context import RunContext

_TEMPLATE_BOILERPLATE = (
    "参考本局有效发言模式",
    "后续归票阶段继续保持",
    "加强沟通",
    "多给有效信息",
)


def _preview(text: str, *, max_len: int = 120) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def build_assets_extraction_prompt(
    *,
    bundle: AssetsPromptBundle,
    ctx: RunContext | None = None,
    ctx_winner_camp: str | None,
    ctx_prompt_version: str,
    llm_analysis: dict[str, Any] | None,
    rule_proposals: list[dict[str, Any]],
    rule_skills: list[dict[str, Any]],
    bad_cases: list[dict[str, Any]],
    mvp_payload: dict[str, Any] | None,
) -> str:
    tpl = bundle.user_template
    lines: list[str] = []
    for line in tpl.get("intro") or []:
        lines.append(str(line))
    lines.append("")

    meta_tpl = tpl.get("meta") or {}
    for _key, fmt in meta_tpl.items():
        lines.append(
            render_template(
                str(fmt),
                winner_camp=ctx_winner_camp or "unknown",
                prompt_version=ctx_prompt_version,
            )
        )
    lines.append("")

    analysis = llm_analysis or {}
    lines.append(str(tpl.get("replay_section_title", "## LLM 复盘摘要")))
    lines.append(
        render_template(
            str(tpl.get("replay_summary", "{replay_summary}")),
            replay_summary=analysis.get("summary_zh") or "（无 LLM 摘要，请依据规则草案与 bad case 提取）",
        )
    )
    suggestions = analysis.get("prompt_suggestions") or []
    if suggestions:
        lines.append(str(tpl.get("replay_suggestions_title", "")))
        sug_line = str(tpl.get("replay_suggestion_line", "- {suggestion}"))
        for item in suggestions:
            lines.append(render_template(sug_line, suggestion=item))
    risks = analysis.get("risks") or []
    if risks:
        lines.append(str(tpl.get("replay_risks_title", "")))
        risk_line = str(tpl.get("replay_risk_line", "- {risk}"))
        for item in risks:
            lines.append(render_template(risk_line, risk=item))
    lines.append("")

    if ctx is not None:
        belief_lines = format_belief_excerpts_for_prompt(ctx)
        if belief_lines:
            lines.append(str(tpl.get("belief_section_title", "## 信念矩阵快照（Skill 触发条件必须引用）")))
            for line in belief_lines:
                lines.append(line)
            lines.append("")

    if bad_cases:
        lines.append(str(tpl.get("bad_case_title", "## Bad Case")))
        bc_line = str(tpl.get("bad_case_line", ""))
        for case in bad_cases:
            evidence = case.get("evidence") or {}
            lines.append(
                render_template(
                    bc_line,
                    kind=case.get("kind", ""),
                    round_number=case.get("round_number", ""),
                    player_id=case.get("player_id", ""),
                    description=case.get("description", ""),
                    suggestion=case.get("suggestion", ""),
                    **evidence,
                )
            )
        lines.append("")

    templated = [
        p
        for p in rule_proposals
        if _is_templated_proposal(p) or p.get("kind") in {"positive_persuasion", "bad_case_rule"}
    ][:12]
    if templated:
        lines.append(str(tpl.get("rule_proposals_title", "")))
        prop_line = str(tpl.get("rule_proposal_line", ""))
        for prop in templated:
            patch = prop.get("suggested_patch") or {}
            lines.append(
                render_template(
                    prop_line,
                    kind=prop.get("kind", ""),
                    role=prop.get("prompt_role_key", ""),
                    confidence=prop.get("confidence_score", ""),
                    patch_preview=_preview(str(patch.get("text_zh") or "")),
                )
            )
        lines.append("")

    if rule_skills:
        lines.append(str(tpl.get("rule_skills_title", "")))
        skill_line = str(tpl.get("rule_skill_line", ""))
        for skill in rule_skills[:8]:
            card = skill.get("skill_card") or {}
            lines.append(
                render_template(
                    skill_line,
                    role=skill.get("prompt_role_key", ""),
                    skill_id=skill.get("skill_id", ""),
                    when_preview=_preview(
                        str(card.get("when_to_use") or card.get("when_to_use_zh") or "")
                    ),
                )
            )
        lines.append("")

    mvp = (mvp_payload or {}).get("mvp") or {}
    golden = mvp.get("golden_speech_candidates") or []
    if golden:
        lines.append(str(tpl.get("mvp_golden_title", "")))
        g_line = str(tpl.get("mvp_golden_line", ""))
        for item in golden[:6]:
            lines.append(
                render_template(
                    g_line,
                    round_number=item.get("round_number", ""),
                    kind=item.get("kind", ""),
                    excerpt=_preview(str(item.get("excerpt") or ""), max_len=200),
                )
            )

    return "\n".join(lines).strip()


def _is_templated_proposal(proposal: dict[str, Any]) -> bool:
    patch = proposal.get("suggested_patch") or {}
    text = str(patch.get("text_zh") or "")
    return any(marker in text for marker in _TEMPLATE_BOILERPLATE)
