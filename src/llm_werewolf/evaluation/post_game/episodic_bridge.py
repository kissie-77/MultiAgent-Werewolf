"""PostGame 与 agent_team 情景记忆（EpisodicMemory）的对接。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

from llm_werewolf.agent_team.memory.episodic_memory import EpisodicMemory
from llm_werewolf.evaluation.post_game.event_adapter import (
    event_logger_from_dicts,
    event_logger_from_engine,
)

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext


def episodic_memory_for_run(ctx: RunContext, *, engine: Any | None = None) -> EpisodicMemory:
    """为赛后分析构建 EpisodicMemory：优先引擎 EventLogger，否则 events.jsonl。"""
    logger = event_logger_from_engine(engine)
    if logger is None or not logger.events:
        logger = event_logger_from_dicts(ctx.events)
    return EpisodicMemory(logger)


def export_player_episode_reports(ctx: RunContext, *, engine: Any | None = None) -> dict[str, Any]:
    """按 roster 导出各玩家 POV 的 episode 复盘（与 MemoryManager 使用同一 API）。"""
    episodic = episodic_memory_for_run(ctx, engine=engine)
    reports: dict[str, Any] = {}
    for player_id in sorted(ctx.roster):
        reports[player_id] = episodic.export_episode_report(player_id)
    return {
        "schema": "episodic_reports_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "player_count": len(reports),
        "by_player": reports,
    }


def episode_excerpt_for_player_round(
    ctx: RunContext,
    player_id: str,
    round_number: int,
    *,
    engine: Any | None = None,
    max_messages: int = 4,
) -> dict[str, Any] | None:
    """单玩家单轮的 episode 摘要，供 Skill 证据 / Coach 引用。"""
    if not player_id:
        return None
    episodic = episodic_memory_for_run(ctx, engine=engine)
    episode = episodic.build_round_episode(player_id, round_number)
    if episode.visible_event_count == 0:
        return None
    key_msgs = episode.key_event_messages[:max_messages]
    decision_msgs = episode.decision_event_messages[:max_messages]
    return {
        "player_id": player_id,
        "round_number": round_number,
        "summary": episode.summary,
        "visible_event_count": episode.visible_event_count,
        "key_event_messages": key_msgs,
        "decision_event_messages": decision_msgs,
    }


def write_episodic_artifacts(ctx: RunContext, *, engine: Any | None = None) -> Path:
    """写出 episodic_reports.json（与情景记忆 export_episode_report 对齐）。"""
    payload = export_player_episode_reports(ctx, engine=engine)
    path = ctx.run_dir / "episodic_reports.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
