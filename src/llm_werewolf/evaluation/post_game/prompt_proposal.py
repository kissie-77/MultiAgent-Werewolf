"""根据对局表现生成 Prompt 提案，仅落盘 JSON，不直接改运行时。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

from llm_werewolf.evaluation.core.checkers import PromptBadCaseChecker
from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.evaluation.post_game.event_adapter import events_from_dicts

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.game_runtime.types import Event
    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import (
        CampSpeechInfluence,
        CampPersuasionReport,
    )


def _events_from_dicts(rows: list[dict[str, Any]]) -> list[Event]:
    return events_from_dicts(rows)


def _role_key_for_speaker(ctx: RunContext, speaker_id: str) -> str:
    entry = ctx.roster.get(speaker_id)
    if entry and entry.role_name:
        return PromptManager.get_prompt_role_key(entry.role_name)
    return "villager"


def _role_key_for_player(ctx: RunContext, player_id: str | None) -> str:
    if not player_id:
        return "villager"
    return _role_key_for_speaker(ctx, player_id)


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


_KEY_VILLAGER_ROLES = frozenset({
    "Seer",
    "Witch",
    "Hunter",
    "Guard",
    "Cupid",
    "Idiot",
    "Elder",
})


def _truncate_at_sentence(text: str, max_len: int = 280) -> str:
    """截断到完整句，避免补丁末尾出现「大家今天都。」这类半句。"""
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    chunk = cleaned[:max_len]
    for sep in ("。", "！", "？", "；", ".", "!", "?"):
        idx = chunk.rfind(sep)
        if idx >= max(40, max_len // 3):
            return chunk[: idx + 1]
    return chunk.rstrip("，,、 ") + "…"


def _sanitize_excerpt_for_role(excerpt: str, role_key: str) -> str:
    """去掉不适合写入目标角色 prompt 的跨身份语境（如守卫金句里的丘比特情侣自证）。"""
    text = excerpt.strip()
    if not text:
        return text
    if role_key == "guard":
        for marker in ("另外", "其次", "而且", "再者"):
            if marker in text:
                tail = text.split(marker, 1)[1].strip()
                if len(tail) >= 20:
                    return f"{marker}{tail}"
    if role_key in {"prophet", "witch", "hunter", "villager"}:
        if "情侣" in text and "丘比特" not in text and "另外" in text:
            tail = text.split("另外", 1)[1].strip()
            if len(tail) >= 20:
                return f"另外{tail}"
    return text


def _eliminations_by_round(ctx: RunContext) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for event in ctx.events:
        if event.get("event_type") != "player_eliminated":
            continue
        rnd = int(event.get("round_number", 0))
        data = event.get("data") or {}
        pid = str(data.get("player_id", ""))
        if pid:
            out[rnd] = {
                "player_id": pid,
                "role": str(data.get("role") or ""),
                "phase": str(event.get("phase") or ""),
            }
    return out


def _proposal_from_mis_elimination(
    ctx: RunContext,
    *,
    round_number: int,
    eliminated_id: str,
    role_name: str,
    idx: int,
) -> dict[str, Any]:
    role_key = PromptManager.get_prompt_role_key(role_name)
    return {
        "proposal_id": f"bad_case_mis_elim_r{round_number}_{eliminated_id}",
        "prompt_role_key": role_key,
        "target_variable": f"{ctx.prompt_version}.role.{role_key}",
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": "bad_case_rule",
        "priority": 90 + idx,
        "confidence_score": 0.78,
        "target_layer": "prompt_rule",
        "evidence_scope": "single_game_quote",
        "suggested_patch": {
            "section": "vote_closing",
            "target_field": "phase_strategies.vote_closing",
            "action": "update_rule",
            "text_zh": (
                "归票前必须核对：目标是否神职、是否已被情侣/丘比特逻辑洗白、"
                "是否与已公开查验或女巫叙事冲突；若无法排除上述风险，不要强行归票。"
            ),
        },
        "evidence": {
            "round_number": round_number,
            "eliminated_player_id": eliminated_id,
            "eliminated_role": role_name,
            "phase": "day_voting",
        },
        "rationale": f"第 {round_number} 轮放逐了好人关键身份 {role_name}，需写入反例约束。",
    }


def _bad_case_patch_for_message(
    message: str,
    role_key: str,
) -> tuple[str, str, str]:
    lowered = message.lower()
    if "empty" in lowered or "too short" in lowered or "too generic" in lowered:
        if role_key in {"wolf", "wolf_king", "white_wolf", "wolf_beauty", "guardian_wolf", "hidden_wolf", "nightmare_wolf", "blood_moon_apostle"}:
            return ("vote_closing", "phase_strategies.vote_closing", "update_rule")
        if role_key in {"prophet", "witch", "hunter", "guard", "villager"}:
            return ("opening", "phase_strategies.opening", "update_rule")
        return ("forbidden_actions", "forbidden_actions", "add_forbidden_rule")
    if "seer checked the same target more than once" in lowered:
        return (
            "night_strategy",
            "phase_strategies.opening",
            "update_rule",
        )
    if "witch poison targeted a villager-camp player" in lowered:
        return (
            "endgame",
            "phase_strategies.endgame",
            "update_rule",
        )
    if "death-shot ability targeted a villager-camp player" in lowered:
        return (
            "vote_closing",
            "phase_strategies.vote_closing",
            "update_rule",
        )
    if "referenced public-day evidence before any public context existed" in lowered:
        return (
            "night_strategy",
            "phase_strategies.opening",
            "update_rule",
        )
    return (
        "global_constraints",
        "global_constraints",
        "append_guidance",
    )


def _bad_case_rule_text(message: str, role_key: str, target_field: str) -> str:
    lowered = message.lower()
    if "empty" in lowered:
        if target_field.startswith("phase_strategies."):
            if role_key.startswith("wolf") or role_key in {
                "white_wolf",
                "wolf_beauty",
                "guardian_wolf",
                "hidden_wolf",
                "nightmare_wolf",
                "blood_moon_apostle",
            }:
                return "白天前半段先抢一个可传播的怀疑目标，归票前必须把结论收束成“今天出谁、为什么、若翻错明天回查谁”，禁止空白或占位发言。"
            return "白天发言即使信息不足，也要先给出一个怀疑对象、一个依据、一个次日观察点，禁止空白、占位或未完成句。"
        return "禁止白天发言只留空白、占位符或未完成句；即使信息少，也要给出至少一个判断对象和理由。"
    if "too short" in lowered:
        if target_field.startswith("phase_strategies."):
            if role_key.startswith("wolf") or role_key in {
                "white_wolf",
                "wolf_beauty",
                "guardian_wolf",
                "hidden_wolf",
                "nightmare_wolf",
                "blood_moon_apostle",
            }:
                return "归票阶段不要只丢座位号；必须同步给出目标收益、票型依据，以及目标翻牌后的下一步叙事。"
            return "开口不要只报座位号或极短结论；至少补齐“怀疑谁、凭什么、接下来想看什么”三段里的两段。"
        return "禁止白天只报座位号或极短结论；发言至少包含目标、依据、以及后续回查方向中的两项。"
    if "too generic" in lowered:
        if target_field.startswith("phase_strategies."):
            if role_key.startswith("wolf") or role_key in {
                "white_wolf",
                "wolf_beauty",
                "guardian_wolf",
                "hidden_wolf",
                "nightmare_wolf",
                "blood_moon_apostle",
            }:
                return "白天不要只讲空泛态度，要把归票目标绑定到具体玩家、具体票型变化或对跳冲突，确保队友能复述你的叙事。"
            return "白天不要只说泛泛态度，必须把判断绑定到具体玩家、票型变化或对跳冲突，保证讨论能继续推进。"
        return "禁止只说“大家谨慎”“再看看”这类空泛话；必须把怀疑对象绑定到具体玩家或具体票型变化。"
    if "seer checked the same target more than once" in lowered:
        return "夜间查验前先排除已查过目标，优先选择能区分场上对立叙事、且次日更容易形成公开验证价值的对象。"
    if "witch poison targeted a villager-camp player" in lowered:
        if target_field.startswith("phase_strategies."):
            return "决定下毒前先核对该目标是否同时满足身份冲突、票型异常、以及收益归属可疑中的至少两项；若做不到，优先保留毒药进入残局。"
        return "禁止在缺乏硬冲突证据时把毒药直接交给好人高概率位；毒药只用于处理强狼面、关键悍跳位或残局轮次点。"
    if "death-shot ability targeted a villager-camp player" in lowered:
        if target_field.startswith("phase_strategies."):
            return "临死开枪前先比较三件事：目标狼面强度、击杀后能否清出新的狼位、以及误带好人的轮次损失；满足前两项再开枪。"
        return "禁止带人技能在没有强狼证据时打向好人高概率位；开枪前先核对票型、站边冲突和收益归属。"
    if "referenced public-day evidence before any public context existed" in lowered:
        return "首夜或尚无公开发言前，夜聊只能依据座位、角色池、狼队信息和刀口收益，不得编造白天发言、票型、活跃度或站边依据；需要推动落刀时给出目标收益和备选目标。"
    return "避免重复出现已知坏例，行动前先核对可见信息边界与当前角色职责。"


def _proposal_from_speech(
    speech: CampSpeechInfluence,
    ctx: RunContext,
    *,
    rank: int,
) -> dict[str, Any]:
    role_key = _role_key_for_speaker(ctx, speech.speaker_id)
    confidence = _clamp_confidence(
        0.45
        + min(0.25, speech.camp_aligned_score * 0.08)
        + min(0.2, speech.camp_aligned_swings * 0.05)
        + (0.1 if speech.matched_round_elimination else 0.0)
    )
    return {
        "proposal_id": f"pos_influence_r{speech.round_number}_{speech.speaker_id}",
        "prompt_role_key": role_key,
        "target_variable": f"{ctx.prompt_version}.role.{role_key}",
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": "positive_persuasion",
        "priority": rank,
        "confidence_score": confidence,
        "target_layer": "prompt_rule",
        "evidence_scope": "multi_game_pattern",
        "suggested_patch": {
            "section": "vote_closing",
            "target_field": "phase_strategies.vote_closing",
            "action": "update_rule",
            "text_zh": (
                "临近归票时主动给出单一投票目标，并用当轮可见信息说明理由；"
                "如果目标翻好人，要同步交代明天优先回查谁。"
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
            f"该发言带来了 {speech.camp_aligned_swings} 次阵营对齐意向波动，"
            f"对齐得分 {speech.camp_aligned_score}。"
            + (" 且与当轮放逐结果方向一致。" if speech.matched_round_elimination else "")
        ),
    }


def _proposal_from_bad_case(check: Any, ctx: RunContext, *, idx: int) -> dict[str, Any]:
    data = check.data or {}
    player_id = str(
        data.get("player_id") or data.get("shooter_id") or ""
    ).strip() or None
    role_key = _role_key_for_player(ctx, player_id)
    section, target_field, action = _bad_case_patch_for_message(
        str(check.message or ""),
        role_key,
    )
    severity_name = str(getattr(check.severity, "name", "WARNING")).upper()
    severity_bonus = {
        "INFO": 0.0,
        "WARNING": 0.08,
        "CRITICAL": 0.18,
    }.get(severity_name, 0.05)
    confidence = _clamp_confidence(data.get("confidence_score") or (0.62 + severity_bonus))
    return {
        "proposal_id": f"bad_case_{idx}",
        "prompt_role_key": role_key,
        "target_variable": (
            f"{ctx.prompt_version}.agent.base"
            if target_field == "global_constraints"
            else f"{ctx.prompt_version}.role.{role_key}"
        ),
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": "bad_case_rule",
        "priority": 100 + idx,
        "confidence_score": confidence,
        "target_layer": "prompt_rule",
        "evidence_scope": "multi_game_pattern",
        "suggested_patch": {
            "section": section,
            "target_field": target_field,
            "action": action,
            "text_zh": _bad_case_rule_text(str(check.message or ""), role_key, target_field),
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
    is_public = kind == "public_persuasion"
    raw_score = float(golden.get("score") or 0.0)
    confidence = _clamp_confidence(
        0.5 + min(0.35, raw_score / 20.0) + (0.08 if golden.get("matched_elimination") else 0.0)
    )
    excerpt_raw = str(golden.get("excerpt") or "").strip()
    excerpt = _truncate_at_sentence(_sanitize_excerpt_for_role(excerpt_raw, role_key))
    return {
        "proposal_id": f"mvp_{kind}_r{golden.get('round_number')}_{speaker_id}",
        "prompt_role_key": role_key,
        "target_variable": f"{ctx.prompt_version}.role.{role_key}",
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": "mvp_golden_quote" if is_public else "mvp_strategy_highlight",
        "priority": rank,
        "confidence_score": confidence,
        "target_layer": "prompt_example" if is_public else "prompt_rule",
        "evidence_scope": "single_game_quote" if is_public else "multi_game_pattern",
        "suggested_patch": {
            "section": "examples" if is_public else "night_strategy",
            "target_field": "examples" if is_public else "phase_strategies.opening",
            "action": "promote_quote_to_example" if is_public else "update_rule",
            "text_zh": (
                excerpt
                if is_public
                else "夜间定刀前先给出可执行的落刀目标与第二顺位备选，方便队友快速统一。"
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
        "rationale": "来自 MVP 评分产物的高价值片段。",
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
        if golden.get("kind", "public_persuasion") == "public_persuasion":
            if not golden.get("matched_elimination"):
                continue
        seen_excerpts.add(excerpt)
        proposals.append(
            _proposal_from_golden_quote(
                {**golden, "player_id": mvp.get("player_id")},
                ctx,
                rank=rank,
            )
        )

    positive = sorted(
        [s for s in camp_report.speeches if s.camp_aligned_score > 0],
        key=lambda s: s.camp_aligned_score,
        reverse=True,
    )[:8]

    seen_proposal_keys: set[str] = set()
    for rank, speech in enumerate(positive, start=len(proposals) + 1):
        if not speech.matched_round_elimination:
            continue
        excerpt = _truncate_at_sentence(speech.public_speech or "", max_len=220)
        dedupe_key = excerpt or speech.speaker_id
        if dedupe_key in seen_proposal_keys:
            continue
        seen_proposal_keys.add(dedupe_key)
        role_key = _role_key_for_speaker(ctx, speech.speaker_id)
        proposal = _proposal_from_speech(speech, ctx, rank=rank)
        if excerpt:
            sanitized = _sanitize_excerpt_for_role(excerpt, role_key)
            proposal["suggested_patch"]["text_zh"] = (
                f"参考本局有效发言模式：{sanitized}。"
                "后续归票阶段继续保持「结论+依据+次日回查」的收束方式。"
            )
        proposals.append(proposal)

    mis_idx = 0
    for rnd, elim in sorted(_eliminations_by_round(ctx).items()):
        if elim.get("phase") != "day_voting":
            continue
        pid = elim["player_id"]
        role_name = elim.get("role") or ""
        entry = ctx.roster.get(pid)
        if entry and entry.camp != Camp.VILLAGER.value:
            continue
        if role_name not in _KEY_VILLAGER_ROLES:
            continue
        proposals.append(_proposal_from_mis_elimination(ctx, round_number=rnd, eliminated_id=pid, role_name=role_name, idx=mis_idx))
        mis_idx += 1

    events = _events_from_dicts(ctx.events)
    if events:
        player_roles = {
            pid: (entry.role_name or "")
            for pid, entry in ctx.roster.items()
            if entry.role_name
        }
        bad_results = PromptBadCaseChecker().check(events, player_roles=player_roles)
        for idx, check in enumerate(bad_results[:10]):
            if not check.passed:
                proposals.append(_proposal_from_bad_case(check, ctx, idx=idx))

    return {
        "schema": "prompt_proposals_v3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version_base": ctx.prompt_version,
        "run_dir": str(ctx.run_dir),
        "winner_camp": ctx.winner_camp,
        "llm_replay_notes": llm_notes,
        "proposal_count": len(proposals),
        "proposals": proposals,
        "apply_policy": "auto_evolve_next_prompt_version",
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
