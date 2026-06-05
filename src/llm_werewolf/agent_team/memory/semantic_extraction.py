"""Runtime semantic candidate extraction (agent_team layer; no evaluation imports)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging

if TYPE_CHECKING:
    from llm_werewolf.agent_team.memory.base import CompressorProtocol
    from llm_werewolf.agent_team.memory.semantic_memory import SemanticMemory

logger = logging.getLogger(__name__)


def extract_semantic_candidates_by_rules(
    report: dict[str, Any],
    *,
    won: bool,
    semantic: SemanticMemory,
    top_k: int,
) -> list[str]:
    candidates: list[str] = []
    for episode in report.get("episodes", []):
        round_number = episode.get("round_number")
        key_messages = episode.get("key_event_messages", [])
        decision_messages = episode.get("decision_event_messages", [])

        if key_messages:
            candidates.append(f"关键局势复盘：第{round_number}轮出现" + "；".join(key_messages[:2]))
        if decision_messages:
            candidates.append(f"决策经验：第{round_number}轮重点关注" + "；".join(decision_messages[:2]))
        if won and key_messages:
            candidates.append(f"胜利经验：第{round_number}轮保留对" + "；".join(key_messages[:1]) + "的持续跟踪")
        if not won and decision_messages:
            candidates.append(
                f"失败反思：第{round_number}轮不要过早依赖"
                + "；".join(decision_messages[:1])
                + "形成判断"
            )

    merged = semantic.merge_reflections(semantic.deduplicate_candidates(candidates))
    return merged[:top_k]


def extract_semantic_candidates_with_llm(
    report: dict[str, Any],
    *,
    won: bool,
    semantic: SemanticMemory,
    compressor: CompressorProtocol | None,
) -> list[str]:
    if compressor is None:
        return []

    lines = [
        "请从以下狼人杀对局记录中提炼 1-3 条可复用的策略经验。",
        "每条不超过 50 字，只输出策略经验列表，不要写流水账。",
        f"本局结果：{'胜利' if won else '失败'}",
    ]
    for episode in report.get("episodes", []):
        messages = episode.get("key_event_messages", []) + episode.get("decision_event_messages", [])
        if messages:
            lines.append(f"第{episode.get('round_number')}轮：" + "；".join(messages[:4]))

    try:
        response = compressor.call_llm_text("\n".join(lines), max_tokens=300)
    except Exception:
        logger.warning("Semantic candidate extraction via LLM failed", exc_info=True)
        return []

    candidates: list[str] = []
    for raw_line in response.splitlines():
        line = raw_line.strip().lstrip("-*0123456789.[] ")
        if line:
            candidates.append(line[:80])
    return semantic.deduplicate_candidates(candidates)


def extract_semantic_candidates(
    report: dict[str, Any],
    *,
    won: bool,
    semantic: SemanticMemory,
    top_k: int,
    enable_llm_extraction: bool = False,
    compressor: CompressorProtocol | None = None,
) -> list[str]:
    if enable_llm_extraction:
        llm_candidates = extract_semantic_candidates_with_llm(
            report,
            won=won,
            semantic=semantic,
            compressor=compressor,
        )
        if llm_candidates:
            return llm_candidates[:top_k]
    return extract_semantic_candidates_by_rules(
        report,
        won=won,
        semantic=semantic,
        top_k=top_k,
    )
