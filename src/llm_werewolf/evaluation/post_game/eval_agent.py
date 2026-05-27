"""PostGame 评测分析师：经 AgentScope ReActAgent 调用（禁止 AsyncOpenAI 旁路）。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.agent_team.agents.factory import create_react_agent
from llm_werewolf.agent_team.invocation.serial_calls import run_serial_agent_call
from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.strategy.evaluation_outputs import ReplayAnalysisDecision

EVAL_ANALYST_SYSTEM_PROMPT = (
    "你是一名狼人杀对局赛后评测分析师。"
    "根据提供的结构化摘要与日志视图，用中文做客观复盘。"
    "不要编造未出现在输入中的私密身份或夜间行动。"
    "输出须符合调用方要求的 JSON 字段。"
)


def _load_analyst_config(config_path: Path | None) -> PlayerConfig | None:
    if config_path is None or not config_path.is_file():
        return None
    try:
        from llm_werewolf.game_runtime.utils import load_config

        players_config = load_config(config_path=config_path)
        if not players_config.players:
            return None
        first = players_config.players[0]
        if first.model.lower() in {"human", "demo"}:
            return None
        if first.api_key_env and not os.getenv(first.api_key_env):
            return None
        return first
    except Exception:
        return None


def _extract_text(response_msg: Any) -> str:
    content = getattr(response_msg, "content", None)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()
    return str(content or "").strip()


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(cleaned)


def build_replay_prompt(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    public_digest: str = "",
    swing_digest: str = "",
) -> str:
    top = sorted(
        camp_report.speeches,
        key=lambda s: s.camp_aligned_score,
        reverse=True,
    )[:5]
    top_lines = []
    for speech in top:
        if speech.camp_aligned_score <= 0:
            continue
        top_lines.append(
            f"- {speech.speaker_name}({speech.speaker_camp}) R{speech.round_number}: "
            f"score={speech.camp_aligned_score}, speech={speech.public_speech[:120]!r}"
        )

    sections = [
        "请根据以下对局摘要写简短复盘，并给出 Prompt 改进建议要点。",
        "",
        f"胜负阵营: {ctx.winner_camp}",
        f"运行时 Prompt 版本: {ctx.prompt_version}",
        f"玩家人数: {len(ctx.roster)}",
        f"结果说明: {ctx.game_result_text or '（无）'}",
        "",
        "阵营匹配的高影响发言:",
        "\n".join(top_lines) if top_lines else "（无正向摇摆）",
    ]
    if public_digest:
        sections.extend(["", "## 公开事件摘要", public_digest[:6000]])
    if swing_digest:
        sections.extend(["", "## 投票意向摇摆摘要", swing_digest[:4000]])
    sections.extend([
        "",
        "请以 JSON 回复，字段: summary_zh (string), prompt_suggestions (string[]), risks (string[])",
    ])
    return "\n".join(sections)


async def run_eval_replay(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    config_path: Path | None = None,
    public_digest: str = "",
    swing_digest: str = "",
) -> dict[str, Any]:
    """经 AgentScope 执行 LLM 复盘；失败时返回降级 dict。"""
    prompt = build_replay_prompt(
        ctx,
        camp_report,
        public_digest=public_digest,
        swing_digest=swing_digest,
    )
    analyst_config = _load_analyst_config(config_path)

    if analyst_config is None:
        return {
            "mode": "skipped",
            "reason": "no_api_config_or_key",
            "backend": "agentscope",
            "summary_zh": "未配置 LLM API，已跳过 LLM 复盘。",
            "prompt_suggestions": [],
            "risks": [],
        }

    try:
        react_agent = create_react_agent(
            analyst_config,
            agent_name="EvalAnalyst",
            sys_prompt=EVAL_ANALYST_SYSTEM_PROMPT,
        )
        user_prompt = (
            f"{prompt}\n\n"
            "请严格以 JSON 回复，字段: summary_zh, prompt_suggestions, risks。"
        )
        input_msg = AgentScopeMsg(name="Moderator", content=user_prompt, role="user")

        response_msg = await run_serial_agent_call(
            lambda: react_agent(input_msg, structured_model=ReplayAnalysisDecision),
        )
        metadata = getattr(response_msg, "metadata", None)
        if isinstance(metadata, dict):
            nested = metadata.get("structured_output")
            if isinstance(nested, dict):
                parsed = ReplayAnalysisDecision.model_validate(nested)
                return {
                    "mode": "llm",
                    "backend": "agentscope",
                    **parsed.model_dump(),
                }

        text = _extract_text(response_msg)
        if not text:
            raise ValueError("empty eval agent response")

        raw = _parse_json_response(text)
        parsed = ReplayAnalysisDecision.model_validate(raw)
        return {
            "mode": "llm",
            "backend": "agentscope",
            **parsed.model_dump(),
        }
    except json.JSONDecodeError as exc:
        return {
            "mode": "failed",
            "backend": "agentscope",
            "reason": str(exc),
            "summary_zh": "LLM 复盘 JSON 解析失败。",
            "prompt_suggestions": [],
            "risks": [str(exc)],
        }
    except Exception as exc:
        return {
            "mode": "failed",
            "backend": "agentscope",
            "reason": str(exc),
            "summary_zh": "LLM 复盘失败，已保留规则分析产物。",
            "prompt_suggestions": [],
            "risks": [str(exc)],
        }
