"""根据阵营正向说服与 bad case 生成 Prompt 补丁提案（仅 JSON，不写入运行时）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.core.checkers import PromptBadCaseChecker
from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport, CampSpeechInfluence
from llm_werewolf.evaluation.post_game.event_adapter import events_from_dicts
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.game_runtime.types import Event


def _events_from_dicts(rows: list[dict[str, Any]]) -> list[Event]:
    return events_from_dicts(rows)


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


def _proposal_from_golden_quote(
    golden: dict[str, Any],
    ctx: RunContext,
    *,
    rank: int,
) -> dict[str, Any]:
    speaker_id = str(golden.get("player_id") or "")
    entry = ctx.roster.get(speaker_id)
    role_key = (
        PromptManager.get_prompt_role_key(entry.role_name)
        if entry and entry.role_name
        else "villager"
    )
    kind = str(golden.get("kind") or "public_persuasion")
    proposal_kind = "mvp_golden_quote" if kind == "public_persuasion" else "mvp_strategy_highlight"
    return {
        "proposal_id": f"mvp_{kind}_r{golden.get('round_number')}_{speaker_id}",
        "prompt_role_key": role_key,
        "target_variable": f"{ctx.prompt_version}.role.{role_key}.suggestion",
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": proposal_kind,
        "priority": rank,
        "suggested_patch": {
            "section": "day_speech_strategy" if kind == "public_persuasion" else "night_strategy",
            "action": "append_guidance",
            "text_zh": (
                "参考本局 MVP 公开说服金句：在可见信息内给出明确票型与理由。"
                if kind == "public_persuasion"
                else "参考本局 MVP 夜间策略：在狼队频道给出可执行的刀口/集火计划。"
            ),
        },
        "evidence": {
            "source": "mvp_scores.json",
            "speaker_id": speaker_id,
            "round_number": golden.get("round_number"),
            "excerpt": golden.get("excerpt"),
            "mvp_score": golden.get("score"),
            "matched_elimination": golden.get("matched_elimination"),
            "kill_match_bonus": golden.get("kill_match_bonus"),
        },
        "rationale": "来自 MVP 规则评分的金句/策略片段（golden_speech_candidates）。",
    }


def build_prompt_proposals(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    llm_notes: str | None = None,
    mvp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proposals: list[dict[str, Any]] = []

    mvp = (mvp_payload or {}).get("mvp") or {}
    seen_excerpts: set[str] = set()
    for rank, golden in enumerate(mvp.get("golden_speech_candidates") or [], start=1):
        excerpt = str(golden.get("excerpt") or "").strip()
        if not excerpt or excerpt in seen_excerpts:
            continue
        seen_excerpts.add(excerpt)
        proposals.append(
            _proposal_from_golden_quote(
                {**golden, "player_id": mvp.get("player_id")},
                ctx,
                rank=rank,
            )
        )
        excerpt = str(golden.get("excerpt") or "").strip()
        if proposals and excerpt:
            proposals[-1]["suggested_patch"]["text_zh"] = (
                f"参考 MVP 金句：「{excerpt[:180]}」"
            )

    positive = sorted(
        [s for s in camp_report.speeches if s.camp_aligned_score > 0],
        key=lambda s: s.camp_aligned_score,
        reverse=True,
    )[:8]

    seen_proposal_keys: set[str] = set()
    for rank, speech in enumerate(positive, start=len(proposals) + 1):
        excerpt = (speech.public_speech or "").strip()[:120]
        dedupe_key = excerpt or speech.speaker_id
        if dedupe_key in seen_proposal_keys:
            continue
        seen_proposal_keys.add(dedupe_key)
        proposal = _proposal_from_speech(speech, ctx, rank=rank)
        proposal["suggested_patch"]["text_zh"] = (
            f"参考本局发言：「{excerpt}…」"
            if excerpt
            else proposal["suggested_patch"]["text_zh"]
        )
        proposals.append(proposal)

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
) -> Path:
    payload = build_prompt_proposals(
        ctx,
        camp_report,
        llm_notes=llm_notes,
        mvp_payload=mvp_payload,
    )
    path = ctx.run_dir / "prompt_proposals.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
