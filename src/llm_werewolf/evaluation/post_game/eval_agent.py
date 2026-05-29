"""PostGame 评测分析师：按维度隔离上下文，禁止喂全局 god 日志。"""

from __future__ import annotations

import os
import json
from typing import TYPE_CHECKING, Any

from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.agent_team.agents.factory import create_react_agent
from llm_werewolf.strategy.evaluation_outputs import ReplayAnalysisDecision
from llm_werewolf.agent_team.invocation.serial_calls import run_serial_agent_call
from llm_werewolf.evaluation.post_game.turning_points import build_rule_summary_zh

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.game_runtime.config import PlayerConfig
    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport

EVAL_ANALYST_SYSTEM_PROMPT = (
    "你是一名狼人杀对局赛后评测分析师。"
    "你只能根据用户提供的「分维度材料」和「MVP 规则分」进行复盘；"
    "不得引用材料中未出现的夜间私密信息、未列出的发言或臆造身份。"
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


def _read_context_file(run_dir: Path, rel_path: str, *, max_chars: int = 5000) -> str:
    path = run_dir / rel_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")[:max_chars]


def build_replay_prompt(
    ctx: RunContext,
    camp_report: CampPersuasionReport | None = None,
    *,
    mvp_payload: dict[str, Any] | None = None,
    dimension_context_paths: dict[str, str] | None = None,
    public_digest: str = "",
    swing_digest: str = "",
) -> str:
    del camp_report, public_digest, swing_digest
    mvp_payload = mvp_payload or {}
    paths = dimension_context_paths or mvp_payload.get("dimension_context_paths") or {}

    sections = [
        "请基于下列「分维度材料」撰写赛后复盘。",
        "规则：每个维度只能使用该维度区块内的记录；不要合并推断未提供的私密夜间信息。",
        "",
        f"胜负阵营: {ctx.winner_camp}",
        f"Prompt 版本: {ctx.prompt_version}",
        f"结果说明: {ctx.game_result_text or '（无）'}",
        "",
        "## MVP 规则评分（已计算，请据此选金句与策略亮点，勿改分）",
        "",
    ]

    mvp = mvp_payload.get("mvp")
    if mvp:
        sections.append(
            f"全场 MVP: {mvp.get('player_name')} ({mvp.get('role_name')}, "
            f"camp={mvp.get('camp')}, score={mvp.get('mvp_total')})"
        )
    for row in (mvp_payload.get("players") or [])[:5]:
        sections.append(
            f"- #{row.get('rank')} {row.get('player_name')}: total={row.get('mvp_total')} "
            f"raw={row.get('breakdown_raw')}"
        )
    golden: list[dict[str, Any]] = []
    if mvp and mvp.get("player_id"):
        for player in mvp_payload.get("players") or []:
            if player.get("player_id") == mvp.get("player_id"):
                golden = player.get("golden_speech_candidates") or []
                break
    if golden:
        sections.extend(["", "### MVP 候选金句/片段", ""])
        for item in golden[:5]:
            sections.append(
                f"- [{item.get('kind')}] R{item.get('round_number')}: {item.get('excerpt', '')[:200]}"
            )

    dim_titles = {
        "persuasion": "公开说服（仅白天公开记录）",
        "wolf_night": "狼队夜间讨论（仅 wolf_team 频道）",
        "strategy": "角色策略执行（仅技能与票型事件）",
        "outcome": "结果贡献（仅投票/出局/刀口/胜负）",
    }
    for dim, title in dim_titles.items():
        rel = paths.get(dim)
        if not rel:
            continue
        body = _read_context_file(ctx.run_dir, rel)
        if not body.strip():
            continue
        sections.extend(["", f"## 维度：{title}", f"（来源 `{rel}`）", "", body])

    dq = mvp_payload.get("data_quality") or {}
    sections.extend([
        "",
        "## 数据质量",
        f"- 公开投票意向: {dq.get('has_vote_intentions')}",
        f"- 狼队频道: {dq.get('has_wolf_team_channel')}",
        f"- 置信度: {dq.get('confidence')}",
        "",
        "请以 JSON 回复，字段: summary_zh (string), prompt_suggestions (string[]), risks (string[])",
        "summary_zh 须点明 MVP 为何是此人（可败方），并引用上述维度中的具体轮次。",
    ])
    return "\n".join(sections)


async def run_eval_replay(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    config_path: Path | None = None,
    mvp_payload: dict[str, Any] | None = None,
    dimension_context_paths: dict[str, str] | None = None,
    public_digest: str = "",
    swing_digest: str = "",
) -> dict[str, Any]:
    prompt = build_replay_prompt(
        ctx,
        camp_report,
        mvp_payload=mvp_payload,
        dimension_context_paths=dimension_context_paths,
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
            analyst_config, agent_name="EvalAnalyst", sys_prompt=EVAL_ANALYST_SYSTEM_PROMPT
        )
        user_prompt = (
            f"{prompt}\n\n请严格以 JSON 回复，字段: summary_zh, prompt_suggestions, risks。"
        )
        input_msg = AgentScopeMsg(name="Moderator", content=user_prompt, role="user")

        response_msg = await run_serial_agent_call(
            lambda: react_agent(input_msg, structured_model=ReplayAnalysisDecision)
        )
        metadata = getattr(response_msg, "metadata", None)
        if isinstance(metadata, dict):
            nested = metadata.get("structured_output")
            if isinstance(nested, dict):
                parsed = ReplayAnalysisDecision.model_validate(nested)
                return {
                    "mode": "llm",
                    "backend": "agentscope",
                    "input_policy": "dimension_scoped_contexts_only",
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
            "input_policy": "dimension_scoped_contexts_only",
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
