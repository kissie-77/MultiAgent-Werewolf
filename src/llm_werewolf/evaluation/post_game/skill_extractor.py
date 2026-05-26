"""按身份从对局素材提取 Skill（Phase 1：生成规则门控，无 benefit 分数筛选）。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.mvp_sources import (
    GoldenQuote,
    build_applicable_scenario,
    build_citations,
    build_situational_background,
    load_mvp_payload,
)
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.evaluation.post_game.skill_generation_rules import (
    SkillGenerationCandidate,
    collect_skill_generation_candidates,
    generation_rules_summary,
)
from llm_werewolf.evaluation.post_game.skill_md import render_skill_markdown


def _slug(text: str, *, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len] or "skill"


def _attach_context_blocks(
    skill: dict[str, Any],
    ctx: RunContext,
    mvp_payload: dict[str, Any] | None,
    *,
    quote: GoldenQuote | None = None,
    speech_round: int | None = None,
    speech_phase: str | None = None,
    excerpt: str | None = None,
) -> None:
    """为 Skill 卡片写入局面背景、适用场景与引用。"""
    card = skill.setdefault("skill_card", {})
    if quote is not None:
        card["background"] = build_situational_background(ctx, quote)
        card["applicable_scenario"] = build_applicable_scenario(quote)
        skill["citations"] = build_citations(ctx, quote, mvp_payload)
        card["when_to_use"] = card.get("applicable_scenario") or card.get("when_to_use")
        return

    rnd = speech_round or skill.get("evidence", {}).get("round_number", 0)
    phase = speech_phase or skill.get("evidence", {}).get("phase", "day_discussion")
    card["background"] = (
        f"对局 `{ctx.run_dir.name}` 第 {rnd} 轮「{phase}」公开讨论；"
        f"本局胜负阵营：{ctx.winner_camp or '未知'}。"
    )
    card["applicable_scenario"] = card.get("when_to_use") or (
        f"第 {rnd} 轮白天讨论，需推动票型与阵营目标一致时。"
    )
    if excerpt:
        skill["citations"] = [
            {
                "ref_id": f"run:{ctx.run_dir.name}",
                "type": "run_directory",
                "path": str(ctx.run_dir),
                "label": "本局产物根目录",
            },
            {
                "ref_id": f"vote_intentions:r{rnd}",
                "type": "vote_intention_record",
                "path": str(ctx.run_dir / "vote_intentions.jsonl"),
                "label": "投票意向记录",
            },
        ]


def _skill_from_candidate(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
    mvp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if candidate.source_kind == "mvp_golden_quote" and candidate.mvp_quote is not None:
        return _skill_from_mvp_quote(candidate, ctx, rank=rank, mvp_payload=mvp_payload)
    if candidate.source_kind == "wolf_night_plan" and candidate.mvp_quote is not None:
        return _skill_from_wolf_night(candidate, ctx, rank=rank, mvp_payload=mvp_payload)
    if candidate.source_kind == "persuasion_speech" and candidate.speech is not None:
        return _skill_from_persuasion(
            candidate, ctx, rank=rank, mvp_payload=mvp_payload,
        )
    return _skill_from_night_action(candidate, ctx, rank=rank, mvp_payload=mvp_payload)


def _skill_from_mvp_quote(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
    mvp_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    quote = candidate.mvp_quote
    assert quote is not None
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_mvp_r{quote.round_number}_{quote.player_id}_{rank}")
    title = f"第{quote.round_number}轮MVP金句说服"
    if quote.is_overall_mvp:
        title = f"第{quote.round_number}轮本场MVP金句"

    skill: dict[str, Any] = {
        "skill_id": skill_id,
        "prompt_role_key": role_key,
        "source_kind": "mvp_golden_quote",
        "source_player_id": candidate.player_id,
        "source_player_name": candidate.player_name,
        "game_role_name": candidate.game_role_name,
        "camp": candidate.camp,
        "source_run": str(ctx.run_dir),
        "status": "draft",
        "mvp_binding": {
            "is_overall_mvp_player": quote.is_overall_mvp,
            "mvp_rank": quote.mvp_rank,
            "golden_kind": quote.kind,
            "golden_score": quote.score,
        },
        "quality_gate": {
            "passed": True,
            "rule_id": candidate.rule.rule_id,
            "reason": candidate.rule.reason,
        },
        "skill_card": {
            "title_zh": title,
            "public_behavior": "直接复用金句中的票型表述与论证结构，保持与当时信息边界一致。",
            "avoid": "空泛重复身份、无票型倾向、越界引用未公开信息",
        },
        "evidence": {
            "round_number": quote.round_number,
            "phase": quote.phase,
            "public_speech_excerpt": quote.excerpt[:400],
            "scores": {"mvp_golden": quote.score},
            **quote.extra,
        },
        "rationale": (
            f"[MVP 金句] 维度得分 {quote.score}。"
            + ("本场 MVP。" if quote.is_overall_mvp else "")
        ),
    }
    _attach_context_blocks(skill, ctx, mvp_payload, quote=quote)
    return skill


def _skill_from_wolf_night(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
    mvp_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    quote = candidate.mvp_quote
    assert quote is not None
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_wolf_r{quote.round_number}_{quote.player_id}_{rank}")

    skill: dict[str, Any] = {
        "skill_id": skill_id,
        "prompt_role_key": role_key,
        "source_kind": "wolf_night_plan",
        "source_player_id": candidate.player_id,
        "source_player_name": candidate.player_name,
        "game_role_name": candidate.game_role_name,
        "camp": candidate.camp,
        "source_run": str(ctx.run_dir),
        "status": "draft",
        "quality_gate": {
            "passed": True,
            "rule_id": candidate.rule.rule_id,
            "reason": candidate.rule.reason,
        },
        "skill_card": {
            "title_zh": f"第{quote.round_number}夜狼队协调计划",
            "public_behavior": "在狼队频道提出明确刀口/抗推对象，并推动队友意向对齐。",
            "avoid": "模糊无刀口、与当晚行动不一致的空话",
        },
        "evidence": {
            "round_number": quote.round_number,
            "phase": quote.phase,
            "wolf_night_excerpt": quote.excerpt[:400],
            "scores": {"wolf_night": quote.score},
            **quote.extra,
        },
        "rationale": f"[狼夜 MVP] 发言维度得分 {quote.score}。",
    }
    _attach_context_blocks(skill, ctx, mvp_payload, quote=quote)
    return skill


def _skill_from_persuasion(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
    mvp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    speech = candidate.speech
    assert speech is not None
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_r{speech.round_number}_{speech.speaker_id}_{rank}")
    title = f"第{speech.round_number}轮阵营正向说服"
    if speech.matched_round_elimination:
        title = f"第{speech.round_number}轮说服并命中放逐"

    skill: dict[str, Any] = {
        "skill_id": skill_id,
        "prompt_role_key": role_key,
        "source_kind": "persuasion_speech",
        "source_player_id": candidate.player_id,
        "source_player_name": candidate.player_name,
        "game_role_name": candidate.game_role_name,
        "camp": candidate.camp,
        "source_run": str(ctx.run_dir),
        "status": "draft",
        "quality_gate": {
            "passed": True,
            "rule_id": candidate.rule.rule_id,
            "reason": candidate.rule.reason,
        },
        "skill_card": {
            "title_zh": title,
            "when_to_use": "白天讨论阶段，需要根据当前可见信息推动同阵营票型一致时",
            "public_behavior": (
                "给出明确票型倾向，并用可见信息解释理由；"
                "参考本局摘录中的表述方式。"
            ),
            "avoid": "空泛重复身份、无票型倾向、越界引用未公开信息",
        },
        "evidence": {
            "round_number": speech.round_number,
            "phase": speech.phase,
            "public_speech_excerpt": (speech.public_speech or "")[:400],
            "camp_aligned_swings": speech.camp_aligned_swings,
            "camp_aligned_score": speech.camp_aligned_score,
            "matched_round_elimination": speech.matched_round_elimination,
            "scores": {
                "intention": speech.camp_aligned_score,
                "benefit": None,
            },
        },
        "rationale": (
            f"[生成规则: {candidate.rule.rule_id}] "
            f"发言后产生 {speech.camp_aligned_swings} 次阵营匹配意向摇摆，"
            f"得分 {speech.camp_aligned_score}。"
            + ("与当轮放逐一致。" if speech.matched_round_elimination else "")
        ),
    }
    if candidate.mvp_quote is not None:
        skill["mvp_binding"] = {
            "golden_kind": candidate.mvp_quote.kind,
            "golden_score": candidate.mvp_quote.score,
            "is_overall_mvp_player": candidate.mvp_quote.is_overall_mvp,
        }
        _attach_context_blocks(skill, ctx, mvp_payload, quote=candidate.mvp_quote)
    else:
        _attach_context_blocks(
            skill,
            ctx,
            mvp_payload,
            speech_round=speech.round_number,
            speech_phase=speech.phase,
            excerpt=(speech.public_speech or "")[:400],
        )
    return skill


def _skill_from_night_action(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
    mvp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = candidate.night_event or {}
    data = event.get("data") or {}
    etype = str(event.get("event_type", "night_action"))
    rnd = int(event.get("round_number", 0))
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_night_r{rnd}_{candidate.player_id}_{rank}")

    title_map = {
        "seer_checked": "预言家有效查验决策",
        "witch_saved": "女巫解药使用决策",
        "witch_poisoned": "女巫毒药使用决策",
        "guard_protected": "守卫守护决策",
        "werewolf_killed": "狼队刀口决策",
    }
    title = title_map.get(etype, f"第{rnd}轮夜间决策")

    skill: dict[str, Any] = {
        "skill_id": skill_id,
        "prompt_role_key": role_key,
        "source_kind": "night_action",
        "source_player_id": candidate.player_id,
        "source_player_name": candidate.player_name,
        "game_role_name": candidate.game_role_name,
        "camp": candidate.camp,
        "source_run": str(ctx.run_dir),
        "status": "draft",
        "quality_gate": {
            "passed": True,
            "rule_id": candidate.rule.rule_id,
            "reason": candidate.rule.reason,
        },
        "skill_card": {
            "title_zh": title,
            "when_to_use": f"第{rnd}轮夜间，面临同类技能抉择且信息边界与当时一致时",
            "public_behavior": "在合法目标集合内做出与阵营收益一致的单一目标选择",
            "avoid": "无效目标、重复无收益操作、泄露不应公开的信息",
        },
        "evidence": {
            "event_type": etype,
            "round_number": rnd,
            "phase": event.get("phase"),
            "target_id": data.get("target_id"),
            "event_message_excerpt": str(event.get("message", ""))[:200],
            "scores": {"intention": None, "benefit": None},
        },
        "rationale": (
            f"[生成规则: {candidate.rule.rule_id}] "
            f"第{rnd}轮 {etype}，目标 {data.get('target_id', '?')}。"
        ),
    }
    _attach_context_blocks(
        skill,
        ctx,
        mvp_payload,
        speech_round=rnd,
        speech_phase=str(event.get("phase", "night")),
    )
    return skill


def build_role_skills(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    mvp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构建 role_skills.json；仅包含通过生成规则的条目。"""
    if mvp_payload is None:
        mvp_payload = load_mvp_payload(ctx.run_dir)
    candidates = collect_skill_generation_candidates(
        ctx, camp_report, mvp_payload=mvp_payload,
    )
    skills = [
        _skill_from_candidate(candidate, ctx, rank=idx, mvp_payload=mvp_payload)
        for idx, candidate in enumerate(candidates, start=1)
    ]

    skipped_summary = _build_skipped_summary(ctx, camp_report, candidates)

    return {
        "schema": "role_skills_v2",
        "mvp_player_id": (mvp_payload or {}).get("mvp", {}).get("player_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "prompt_version_base": ctx.prompt_version,
        "winner_camp": ctx.winner_camp,
        "extraction_mode": "generation_rules",
        "generation_rules": generation_rules_summary(),
        "skill_count": len(skills),
        "skills": skills,
        "skipped_identities": skipped_summary,
        "apply_policy": "md_and_agent_library_draft",
    }


def _build_skipped_summary(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    candidates: list[SkillGenerationCandidate],
) -> list[dict[str, Any]]:
    """记录本局有玩家但未生成 Skill 的身份（仅 JSON 摘要，不写 MD）。"""
    from llm_werewolf.evaluation.post_game.skill_generation_rules import (
        evaluate_persuasion_speech,
    )
    from llm_werewolf.game_runtime.prompts.manager import PromptManager

    generated_roles = {c.prompt_role_key for c in candidates}
    roster_roles: dict[str, list[str]] = {}
    for pid, entry in ctx.roster.items():
        if not entry.role_name:
            continue
        key = PromptManager.get_prompt_role_key(entry.role_name)
        roster_roles.setdefault(key, []).append(pid)

    skipped: list[dict[str, Any]] = []
    for role_key, player_ids in sorted(roster_roles.items()):
        if role_key in generated_roles:
            continue
        reasons: list[str] = []
        for speech in camp_report.speeches:
            if speech.speaker_id not in player_ids:
                continue
            result = evaluate_persuasion_speech(speech)
            if not result.passed:
                reasons.append(result.reason)
        skipped.append({
            "prompt_role_key": role_key,
            "player_ids": player_ids,
            "reason": reasons[0] if reasons else "no qualifying speech or night action",
        })
    return skipped


def write_skill_markdown_files(
    skills: list[dict[str, Any]],
    *,
    run_skills_dir: Path,
    agent_skills_root: Path,
) -> list[str]:
    """写入 run 目录与 agent_team/skills/<role>/ 下的 MD 文件。"""
    written: list[str] = []
    for skill in skills:
        if skill.get("status") == "skipped":
            continue
        role_key = str(skill.get("prompt_role_key") or "villager")
        skill_id = str(skill.get("skill_id") or "skill")
        filename = f"{skill_id}.md"
        body = render_skill_markdown(skill)

        run_path = run_skills_dir / filename
        run_skills_dir.mkdir(parents=True, exist_ok=True)
        run_path.write_text(body, encoding="utf-8")
        written.append(f"skills/{filename}")

        role_dir = agent_skills_root / role_key
        role_dir.mkdir(parents=True, exist_ok=True)
        agent_path = role_dir / filename
        agent_path.write_text(body, encoding="utf-8")
        skill["md_path"] = str(run_path)
        skill["agent_skill_path"] = str(agent_path)
        written.append(f"agent_team/skills/{role_key}/{filename}")

    return written


def write_role_skills_artifacts(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    agent_skills_root: Path | None = None,
    mvp_payload: dict[str, Any] | None = None,
) -> Path:
    """写出 role_skills.json 与 Skill MD（run + agent 双写）。"""
    if agent_skills_root is None:
        from llm_werewolf.agent_team.skill_loader import agent_skills_root as default_root

        agent_skills_root = default_root()

    payload = build_role_skills(ctx, camp_report, mvp_payload=mvp_payload)
    skills = payload["skills"]
    md_files = write_skill_markdown_files(
        skills,
        run_skills_dir=ctx.run_dir / "skills",
        agent_skills_root=agent_skills_root,
    )
    payload["md_files"] = md_files

    path = ctx.run_dir / "role_skills.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
