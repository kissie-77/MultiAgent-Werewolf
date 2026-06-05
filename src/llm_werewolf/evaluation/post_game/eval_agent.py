"""PostGame 评测分析师：按维度隔离上下文，禁止喂全局 god 日志。"""

from __future__ import annotations

import os
import json
from typing import TYPE_CHECKING, Any
import asyncio

from pydantic import ValidationError
from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.agent_team.agents.factory import create_react_agent
from llm_werewolf.agent_team.agents.agentscope_agent import (
    _extract_structured_payload_from_content,
)
from llm_werewolf.agent_team.invocation.serial_calls import run_serial_agent_call
from llm_werewolf.evaluation.post_game.turning_points import build_rule_summary_zh
from llm_werewolf.strategy.contracts.evaluation_outputs import ReplayAnalysisDecision
from llm_werewolf.agent_team.invocation.structured_invoke import (
    unwrap_structured_metadata,
    generate_response_instruction,
)
from llm_werewolf.evaluation.post_game.replay_prompt_builder import build_replay_prompt
from llm_werewolf.evaluation.registry.post_game_prompt_registry import load_replay_prompt_bundle

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.game_runtime.config import PlayerConfig
    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport


def _load_analyst_config(config_path: Path | None) -> PlayerConfig | None:
    if config_path is None or not config_path.is_file():
        return None
    try:
        from llm_werewolf.game_runtime.support.utils import load_config

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
    if hasattr(response_msg, "get_text_content"):
        text = response_msg.get_text_content()
        if text:
            return text.strip()
    content = getattr(response_msg, "content", None)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "thinking":
                    continue
                if block_type == "text":
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content or "").strip()


def _parse_replay_decision(response_msg: Any) -> ReplayAnalysisDecision | None:
    """从 metadata、tool_use 或文本 JSON 恢复 ReplayAnalysisDecision。"""
    metadata = unwrap_structured_metadata(getattr(response_msg, "metadata", None))
    if not metadata:
        metadata = _extract_structured_payload_from_content(
            getattr(response_msg, "content", None)
        )
    if metadata:
        try:
            return ReplayAnalysisDecision.model_validate(metadata)
        except ValidationError:
            pass

    text = _extract_text(response_msg)
    if not text or text == "Structured response submitted.":
        return None
    try:
        return ReplayAnalysisDecision.model_validate(_parse_json_response(text))
    except (json.JSONDecodeError, ValidationError):
        return None


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(cleaned)


async def _invoke_eval_analyst(
    react_agent: Any,
    user_prompt: str,
    *,
    plain_json_fallback: str,
) -> ReplayAnalysisDecision:
    """结构化调用 eval analyst，含 429 重试与 plain JSON fallback。"""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            input_msg = AgentScopeMsg(name="Moderator", content=user_prompt, role="user")
            response_msg = await run_serial_agent_call(
                lambda: react_agent(input_msg, structured_model=ReplayAnalysisDecision)
            )
            parsed = _parse_replay_decision(response_msg)
            if parsed is not None:
                return parsed
            last_error = ValueError("empty eval agent response")
        except Exception as exc:
            last_error = exc
            if "429" in str(exc) and attempt < 2:
                await asyncio.sleep(2**attempt)
                continue

    plain_prompt = f"{user_prompt}\n\n{plain_json_fallback}"
    plain_msg = AgentScopeMsg(name="Moderator", content=plain_prompt, role="user")
    try:
        response_msg = await run_serial_agent_call(lambda: react_agent(plain_msg))
        parsed = _parse_replay_decision(response_msg)
        if parsed is not None:
            return parsed
    except Exception as exc:
        last_error = exc

    if last_error is not None:
        raise last_error
    msg = "empty eval agent response"
    raise ValueError(msg)


async def run_eval_replay(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    config_path: Path | None = None,
    mvp_payload: dict[str, Any] | None = None,
    dimension_context_paths: dict[str, str] | None = None,
    public_digest: str = "",
    swing_digest: str = "",
    replay_prompt_version: str | None = None,
) -> dict[str, Any]:
    del camp_report, public_digest, swing_digest
    prompt_bundle = load_replay_prompt_bundle(replay_prompt_version)
    prompt = build_replay_prompt(
        ctx,
        mvp_payload=mvp_payload,
        dimension_context_paths=dimension_context_paths,
        prompt_version=prompt_bundle.version,
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
            sys_prompt=prompt_bundle.system_prompt,
        )
        user_prompt = (
            f"{prompt}\n\n{prompt_bundle.json_reminder}\n\n"
            f"{generate_response_instruction('ReplayAnalysisDecision')}"
        )
        parsed = await _invoke_eval_analyst(
            react_agent,
            user_prompt,
            plain_json_fallback=prompt_bundle.plain_json_fallback,
        )

        return {
            "mode": "llm",
            "backend": "agentscope",
            "input_policy": "dimension_scoped_contexts_only",
            "replay_prompt_version": prompt_bundle.version,
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
            "summary_zh": build_rule_summary_zh(ctx),
            "prompt_suggestions": [],
            "risks": [str(exc)],
        }
