"""根据阵营正向说服与 bad case 生成 Prompt 补丁提案（仅 JSON，不写入运行时）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.correctness.checkers import PromptBadCaseChecker
from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport, CampSpeechInfluence
from llm_werewolf.evaluation.post_game.mvp_sources import (
    GoldenQuote,
    build_applicable_scenario,
    build_citations,
    build_situational_background,
    iter_golden_quotes,
    load_mvp_payload,
)
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.game_runtime.types import Event
from llm_werewolf.game_runtime.types.enums import EventType, GamePhase


def _events_from_dicts(rows: list[dict[str, Any]]) -> list[Event]:
    events: list[Event] = []
    for raw in rows:
        try:
            phase_raw = str(raw.get("phase", "setup"))
            events.append(
                Event(
                    event_type=EventType(raw["event_type"]),
                    message=str(raw.get("message", "")),
                    round_number=int(raw.get("round_number", 0)),
                    phase=GamePhase(phase_raw),
                    data=raw.get("data") or {},
                    visible_to=raw.get("visible_to"),
                )
            )
        except (ValueError, KeyError):
            continue
    return events


def _role_key_for_speaker(ctx: RunContext, speaker_id: str) -> str:
    entry = ctx.roster.get(speaker_id)
    if entry and entry.role_name:
        return PromptManager.get_prompt_role_key(entry.role_name)
    return "villager"


def _proposal_from_speech(
    speech: CampSpeechInfluence,
    ctx: RunContext,
    *,
    rank: int,
) -> dict[str, Any]:
    role_key = _role_key_for_speaker(ctx, speech.speaker_id)
    target_var = f"{ctx.prompt_version}.role.{role_key}.suggestion"
    return {
        "proposal_id": f"pos_influence_r{speech.round_number}_{speech.speaker_id}",
        "prompt_role_key": role_key,
        "target_variable": target_var,
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": "positive_persuasion",
        "priority": rank,
        "suggested_patch": {
            "section": "day_speech_strategy",
            "action": "append_guidance",
            "text_zh": (
                "参考本局高阵营收益发言：在公开讨论中给出明确票型倾向，"
                "用当前可见信息支撑，并推动队友/好人阵营意向与你方目标一致。"
            ),
        },
        "evidence": {
            "speaker_id": speech.speaker_id,
            "speaker_camp": speech.speaker_camp,
            "round_number": speech.round_number,
            "camp_aligned_score": speech.camp_aligned_score,
            "camp_aligned_swings": speech.camp_aligned_swings,
            "matched_round_elimination": speech.matched_round_elimination,
            "public_speech_excerpt": speech.public_speech[:300],
        },
        "rationale": (
            f"发言后产生 {speech.camp_aligned_swings} 次阵营匹配的意向摇摆，"
            f"得分 {speech.camp_aligned_score}。"
            + ("且与当轮放逐票型一致。" if speech.matched_round_elimination else "")
        ),
    }


def _patch_section_for_kind(kind: str) -> str:
    if kind == "wolf_night_plan":
        return "wolf_night_coordination"
    return "day_speech_strategy"


def _proposal_from_golden(
    quote: GoldenQuote,
    ctx: RunContext,
    mvp_payload: dict[str, Any] | None,
    *,
    rank: int,
) -> dict[str, Any]:
    role_key = quote.prompt_role_key
    target_var = f"{ctx.prompt_version}.role.{role_key}.suggestion"
    section = _patch_section_for_kind(quote.kind)
    kind_label = "mvp_golden_speech" if quote.is_overall_mvp else "golden_speech"
    mvp_player_id = (mvp_payload or {}).get("mvp", {}).get("player_id")

    template_hint = (
        "狼夜协调：先报刀口/抗推对象，再请队友对齐意向。"
        if quote.kind == "wolf_night_plan"
        else "可模仿该句式：明确票型 + 用当前可见信息给出理由。"
    )

    return {
        "proposal_id": f"{kind_label}_r{quote.round_number}_{quote.player_id}",
        "prompt_role_key": role_key,
        "target_variable": target_var,
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": kind_label,
        "priority": rank,
        "mvp_binding": {
            "mvp_player_id": mvp_player_id,
            "source_player_id": quote.player_id,
            "quote_kind": quote.kind,
            "mvp_rank": quote.mvp_rank,
            "golden_score": quote.score,
            "is_overall_mvp_player": quote.is_overall_mvp,
        },
        "suggested_patch": {
            "section": section,
            "action": "append_example",
            "text_zh": quote.excerpt[:800],
            "template_hint": template_hint,
        },
        "background": build_situational_background(ctx, quote),
        "applicable_scenario": build_applicable_scenario(quote),
        "citations": build_citations(ctx, quote, mvp_payload),
        "evidence": {
            "speaker_id": quote.player_id,
            "speaker_name": quote.player_name,
            "camp": quote.camp,
            "round_number": quote.round_number,
            "phase": quote.phase,
            "public_speech_excerpt": quote.excerpt[:500],
            "golden_kind": quote.kind,
            "mvp_score": quote.score,
            **quote.extra,
        },
        "rationale": (
            f"MVP 维度金句（{quote.kind}），得分 {quote.score}。"
            + ("本场 MVP 玩家。" if quote.is_overall_mvp else "")
        ),
    }


def _proposals_from_llm_analysis(
    ctx: RunContext,
    llm_analysis: dict[str, Any] | None,
    *,
    start_priority: int = 40,
) -> list[dict[str, Any]]:
    """将复盘 LLM 结构化建议写入 proposals（kind=llm_suggestion）。"""
    if not llm_analysis or llm_analysis.get("mode") != "llm":
        return []

    proposals: list[dict[str, Any]] = []
    suggestions = llm_analysis.get("prompt_suggestions") or []
    if not suggestions and llm_analysis.get("summary_zh"):
        suggestions = [str(llm_analysis["summary_zh"])[:500]]

    for idx, text in enumerate(suggestions[:5]):
        text = str(text).strip()
        if len(text) < 6:
            continue
        proposals.append({
            "proposal_id": f"llm_suggestion_{idx}",
            "prompt_role_key": "villager",
            "target_variable": f"{ctx.prompt_version}.agent.base",
            "prompt_version_base": ctx.prompt_version,
            "status": "draft",
            "kind": "llm_suggestion",
            "priority": start_priority + idx,
            "suggested_patch": {
                "section": "agent_guidance",
                "action": "append_guidance",
                "text_zh": text[:800],
            },
            "evidence": {
                "source": "post_game_analysis.json",
                "summary_zh": (llm_analysis.get("summary_zh") or "")[:300],
                "risks": llm_analysis.get("risks") or [],
            },
            "rationale": "评测分析师 LLM 复盘建议（AgentScope structured output）",
        })
    return proposals


def _proposal_from_bad_case(
    check: Any,
    ctx: RunContext,
    *,
    idx: int,
) -> dict[str, Any]:
    data = check.data or {}
    return {
        "proposal_id": f"bad_case_{idx}",
        "prompt_role_key": "villager",
        "target_variable": f"{ctx.prompt_version}.agent.base",
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": "bad_case_rule",
        "priority": 100 + idx,
        "suggested_patch": {
            "section": "global_constraints",
            "action": "append_guidance",
            "text_zh": "避免空泛发言、重复无效查验目标、越界座位号引用；遵守当前人数与可见信息边界。",
        },
        "evidence": data,
        "rationale": check.message,
    }


def build_prompt_proposals(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    llm_notes: str | None = None,
    mvp_payload: dict[str, Any] | None = None,
    llm_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if mvp_payload is None:
        mvp_payload = load_mvp_payload(ctx.run_dir)

    proposals: list[dict[str, Any]] = []
    seen_golden: set[tuple[str, int, str]] = set()

    goldens = iter_golden_quotes(mvp_payload, ctx)
    for rank, quote in enumerate(goldens[:12], start=1):
        key = (quote.player_id, quote.round_number, quote.excerpt[:80])
        if key in seen_golden:
            continue
        seen_golden.add(key)
        proposals.append(
            _proposal_from_golden(quote, ctx, mvp_payload, rank=rank),
        )

    # 无 MVP 金句时回退阵营说服榜
    if not proposals:
        positive = sorted(
            [s for s in camp_report.speeches if s.camp_aligned_score > 0],
            key=lambda s: s.camp_aligned_score,
            reverse=True,
        )[:8]
        for rank, speech in enumerate(positive, start=50):
            proposals.append(_proposal_from_speech(speech, ctx, rank=rank))

    proposals.extend(_proposals_from_llm_analysis(ctx, llm_analysis))

    events = _events_from_dicts(ctx.events)
    if events:
        player_roles = {
            pid: (e.role_name or "")
            for pid, e in ctx.roster.items()
            if e.role_name
        }
        bad_results = PromptBadCaseChecker().check(events, player_roles=player_roles)
        for idx, check in enumerate(bad_results[:10]):
            if not check.passed:
                proposals.append(_proposal_from_bad_case(check, ctx, idx=idx))

    return {
        "schema": "prompt_proposals_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version_base": ctx.prompt_version,
        "run_dir": str(ctx.run_dir),
        "winner_camp": ctx.winner_camp,
        "mvp_player_id": (mvp_payload or {}).get("mvp", {}).get("player_id"),
        "proposal_source": "mvp_golden_quotes" if goldens else "camp_persuasion_fallback",
        "llm_replay_notes": llm_notes,
        "proposal_count": len(proposals),
        "proposals": proposals,
        "apply_policy": "json_only_no_runtime_replace",
    }


def write_prompt_proposals(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    llm_notes: str | None = None,
    mvp_payload: dict[str, Any] | None = None,
    llm_analysis: dict[str, Any] | None = None,
) -> Path:
    payload = build_prompt_proposals(
        ctx,
        camp_report,
        llm_notes=llm_notes,
        mvp_payload=mvp_payload,
        llm_analysis=llm_analysis,
    )
    path = ctx.run_dir / "prompt_proposals.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
