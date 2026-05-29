"""按身份从对局素材提取 Skill（Phase 1：生成规则门控，无 benefit 分数筛选）。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.evaluation.post_game.skill_generation.skill_card_builder import (
    build_night_action_skill_card,
    build_persuasion_skill_card,
)
from llm_werewolf.evaluation.post_game.skill_generation.skill_generation_rules import (
    SkillGenerationCandidate,
    collect_skill_generation_candidates,
    collect_skipped_candidates,
    generation_rules_summary,
)
from llm_werewolf.evaluation.post_game.skill_generation.skill_md import render_skill_markdown


def _slug(text: str, *, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len] or "skill"


def _skill_from_candidate(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
) -> dict[str, Any]:
    if candidate.source_kind == "persuasion_speech" and candidate.speech is not None:
        return _skill_from_persuasion(candidate, ctx, rank=rank)
    return _skill_from_night_action(candidate, ctx, rank=rank)


def _skill_from_persuasion(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
) -> dict[str, Any]:
    speech = candidate.speech
    assert speech is not None
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_r{speech.round_number}_{speech.speaker_id}_{rank}")
    card = build_persuasion_skill_card(role_key=role_key, speech=speech, ctx=ctx)

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "skill_id": skill_id,
        "prompt_role_key": role_key,
        "source_kind": "persuasion_speech",
        "source_player_id": candidate.player_id,
        "source_player_name": candidate.player_name,
        "game_role_name": candidate.game_role_name,
        "camp": candidate.camp,
        "source_run": str(ctx.run_dir),
        "status": "draft",
        "weight": 1.0,
        "win_count": 0,
        "use_count": 0,
        "created_at": now_iso,
        "updated_at": now_iso,
        "quality_gate": {
            "passed": True,
            "rule_id": candidate.rule.rule_id,
            "reason": candidate.rule.reason,
        },
        "skill_card": {
            "title_zh": card.title_zh,
            "when_to_use": card.when_to_use,
            "public_behavior": card.public_behavior,
            "avoid": card.avoid,
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


def _skill_from_night_action(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
) -> dict[str, Any]:
    event = candidate.night_event or {}
    data = event.get("data") or {}
    etype = str(event.get("event_type", "night_action"))
    rnd = int(event.get("round_number", 0))
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_night_r{rnd}_{candidate.player_id}_{rank}")
    card = build_night_action_skill_card(role_key=role_key, event=event, ctx=ctx)
    check_result = data.get("result")

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "skill_id": skill_id,
        "prompt_role_key": role_key,
        "source_kind": "night_action",
        "source_player_id": candidate.player_id,
        "source_player_name": candidate.player_name,
        "game_role_name": candidate.game_role_name,
        "camp": candidate.camp,
        "source_run": str(ctx.run_dir),
        "status": "draft",
        "weight": 1.0,
        "win_count": 0,
        "use_count": 0,
        "created_at": now_iso,
        "updated_at": now_iso,
        "quality_gate": {
            "passed": True,
            "rule_id": candidate.rule.rule_id,
            "reason": candidate.rule.reason,
        },
        "skill_card": {
            "title_zh": card.title_zh,
            "when_to_use": card.when_to_use,
            "public_behavior": card.public_behavior,
            "avoid": card.avoid,
        },
        "evidence": {
            "event_type": etype,
            "round_number": rnd,
            "phase": event.get("phase"),
            "target_id": data.get("target_id"),
            "check_result": check_result,
            "event_message_excerpt": str(event.get("message", ""))[:200],
            "scores": {"intention": None, "benefit": None},
        },
        "rationale": (
            f"[生成规则: {candidate.rule.rule_id}] "
            f"第{rnd}轮 {etype}，目标 {data.get('target_id', '?')}"
            + (f"，结果 {check_result}。" if check_result else "。")
        ),
    }


def build_role_skills(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
) -> dict[str, Any]:
    """构建 role_skills.json；仅包含通过生成规则的条目。"""
    candidates = collect_skill_generation_candidates(ctx, camp_report)
    skills = [
        _skill_from_candidate(candidate, ctx, rank=idx)
        for idx, candidate in enumerate(candidates, start=1)
    ]

    skipped = collect_skipped_candidates(ctx, camp_report)
    skipped_summary = _build_skipped_summary(ctx, camp_report, candidates)

    return {
        "schema": "role_skills_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "prompt_version_base": ctx.prompt_version,
        "winner_camp": ctx.winner_camp,
        "extraction_mode": "generation_rules",
        "generation_rules": generation_rules_summary(),
        "skill_count": len(skills),
        "skills": skills,
        "skipped_identities": skipped_summary,
        "skipped_candidates": [
            {
                "source_kind": s.source_kind,
                "player_id": s.player_id,
                "player_name": s.player_name,
                "rule_id": s.rule_id,
                "reason": s.reason,
            }
            for s in skipped
        ],
        "apply_policy": "run_scoped_md_only",
    }


def _build_skipped_summary(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    candidates: list[SkillGenerationCandidate],
) -> list[dict[str, Any]]:
    """记录本局有玩家但未生成 Skill 的身份（仅 JSON 摘要，不写 MD）。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_generation_rules import (
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
            result = evaluate_persuasion_speech(speech, ctx)
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
    agent_skills_root: Path | None = None,
) -> list[str]:
    """写入 run 目录下的 Skill MD；可选双写 agent_team/skills。"""
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
        skill["md_path"] = str(run_path)

        if agent_skills_root is not None:
            role_dir = agent_skills_root / role_key
            role_dir.mkdir(parents=True, exist_ok=True)
            agent_path = role_dir / filename
            agent_path.write_text(body, encoding="utf-8")
            skill["agent_skill_path"] = str(agent_path)
            written.append(f"agent_team/skills/{role_key}/{filename}")

    return written


def write_role_skills_artifacts(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    agent_skills_root: Path | None = None,
    write_agent_library: bool = False,
) -> Path:
    """写出 role_skills.json 与 Skill MD（默认仅 run 目录）。"""
    if agent_skills_root is None:
        from llm_werewolf.agent_team.skill_support.skill_loader import agent_skills_root as default_root

        agent_skills_root = default_root()

    payload = build_role_skills(ctx, camp_report)
    skills = payload["skills"]

    from llm_werewolf.agent_team.skill_support import skill_loader

    skill_loader.list_role_skill_files.cache_clear()

    md_files = write_skill_markdown_files(
        skills,
        run_skills_dir=ctx.run_dir / "skills",
        agent_skills_root=agent_skills_root if write_agent_library else None,
    )
    payload["md_files"] = md_files

    path = ctx.run_dir / "role_skills.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
