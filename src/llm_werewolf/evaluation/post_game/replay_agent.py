"""赛后 LLM 复盘（可选；失败时降级为规则摘要）。

v2：经 ``eval_agent`` + AgentScope 调用，不再使用 AsyncOpenAI 旁路。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from llm_werewolf.evaluation.post_game.eval_agent import run_eval_replay

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport


async def run_llm_replay(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    config_path: Path | None = None,
    mvp_payload: dict[str, Any] | None = None,
    dimension_context_paths: dict[str, str] | None = None,
    public_digest: str = "",
    swing_digest: str = "",
) -> dict[str, Any]:
    """兼容旧接口；内部走 AgentScope eval_agent。"""
    return await run_eval_replay(
        ctx,
        camp_report,
        config_path=config_path,
        mvp_payload=mvp_payload,
        dimension_context_paths=dimension_context_paths,
        public_digest=public_digest,
        swing_digest=swing_digest,
    )


def write_post_game_analysis(ctx: RunContext, analysis: dict[str, Any]) -> Path:
    path = ctx.run_dir / "post_game_analysis.json"
    payload = {"run_dir": str(ctx.run_dir), "prompt_version": ctx.prompt_version, **analysis}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = ctx.run_dir / "post_game_report.md"
    suggestions = analysis.get("prompt_suggestions") or []
    lines = [
        "# Post-Game Analysis",
        "",
        f"- Mode: **{analysis.get('mode', 'unknown')}**",
        f"- Prompt version: **{ctx.prompt_version}**",
        "",
        "## Summary",
        "",
        str(analysis.get("summary_zh", "")),
        "",
    ]
    if suggestions:
        lines.append("## Prompt suggestions (LLM)")
        lines.append("")
        for item in suggestions:
            lines.append(f"- {item}")
        lines.append("")
    risks = analysis.get("risks") or []
    if risks:
        lines.append("## Risks / notes")
        lines.append("")
        for item in risks:
            lines.append(f"- {item}")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return path
