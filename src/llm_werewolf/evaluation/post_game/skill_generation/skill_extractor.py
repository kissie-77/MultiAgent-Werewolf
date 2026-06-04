"""按身份从对局素材提取 Skill（Phase 1：生成规则门控，无 benefit 分数筛选）。"""

from __future__ import annotations

import re
import json
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

from llm_werewolf.agent_team.skill_support.skill_loader import is_trusted_source_run
from llm_werewolf.evaluation.post_game.skill_generation.skill_md import render_skill_markdown
from llm_werewolf.evaluation.post_game.skill_generation.skill_card_builder import (
    BeliefDistributionSummary,
    BeliefRunIndex,
    build_belief_when_clause,
    build_persuasion_skill_card,
    build_night_action_skill_card,
    generalize_seat_references,
)
from llm_werewolf.evaluation.post_game.skill_generation.skill_generation_rules import (
    SkillGenerationCandidate,
    generation_rules_summary,
    collect_skipped_candidates,
    collect_skill_generation_candidates,
)

_ACTIVATE_WEIGHT_THRESHOLD = 1.05
_DEPRECATE_WEIGHT_THRESHOLD = 0.95
_WINNING_SKILL_WEIGHT_DELTA = 0.10
_LOSING_SKILL_WEIGHT_DELTA = -0.05
_MERGE_WEIGHT_DELTA = 0.15
_WHEN_TO_USE_MATCH_THRESHOLD = 0.78

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport


def _slug(text: str, *, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len] or "skill"


def _skill_from_candidate(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
    belief_index: BeliefRunIndex | None = None,
) -> dict[str, Any]:
    if candidate.source_kind == "persuasion_speech" and candidate.speech is not None:
        return _skill_from_persuasion(candidate, ctx, rank=rank, belief_index=belief_index)
    return _skill_from_night_action(candidate, ctx, rank=rank, belief_index=belief_index)


def _resolve_belief_summary(
    candidate: SkillGenerationCandidate,
    *,
    belief_index: BeliefRunIndex | None,
) -> BeliefDistributionSummary | None:
    if belief_index is None or not belief_index.rows:
        return None
    if candidate.source_kind == "persuasion_speech" and candidate.speech is not None:
        snapshot = belief_index.find_persuasion_snapshot(
            observer_id=candidate.player_id,
            round_number=candidate.speech.round_number,
            phase=candidate.speech.phase or "day_discussion",
        )
    else:
        event = candidate.night_event or {}
        snapshot = belief_index.find_night_snapshot(
            observer_id=candidate.player_id,
            round_number=int(event.get("round_number", 0) or 0),
        )
    return build_belief_when_clause(snapshot)


def _skill_from_persuasion(
    candidate: SkillGenerationCandidate,
    ctx: RunContext,
    *,
    rank: int,
    belief_index: BeliefRunIndex | None = None,
) -> dict[str, Any]:
    speech = candidate.speech
    assert speech is not None
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_r{speech.round_number}_persuasion_{rank}")
    belief_summary = _resolve_belief_summary(candidate, belief_index=belief_index)
    card = build_persuasion_skill_card(
        role_key=role_key,
        speech=speech,
        ctx=ctx,
        belief_summary=belief_summary,
    )

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
            "when_to_use": generalize_seat_references(card.when_to_use),
            "public_behavior": generalize_seat_references(card.public_behavior),
            "avoid": card.avoid,
        },
        "evidence": {
            "round_number": speech.round_number,
            "phase": speech.phase,
            "public_speech_excerpt": (speech.public_speech or "")[:400],
            "camp_aligned_swings": speech.camp_aligned_swings,
            "camp_aligned_score": speech.camp_aligned_score,
            "matched_round_elimination": speech.matched_round_elimination,
            "belief_context": belief_summary.to_evidence() if belief_summary else None,
            "scores": {"intention": speech.camp_aligned_score, "benefit": None},
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
    belief_index: BeliefRunIndex | None = None,
) -> dict[str, Any]:
    event = candidate.night_event or {}
    data = event.get("data") or {}
    etype = str(event.get("event_type", "night_action"))
    rnd = int(event.get("round_number", 0))
    role_key = candidate.prompt_role_key
    skill_id = _slug(f"{role_key}_night_r{rnd}_{etype}_{rank}")
    belief_summary = _resolve_belief_summary(candidate, belief_index=belief_index)
    card = build_night_action_skill_card(
        role_key=role_key,
        event=event,
        ctx=ctx,
        belief_summary=belief_summary,
    )
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
            "when_to_use": generalize_seat_references(card.when_to_use),
            "public_behavior": generalize_seat_references(card.public_behavior),
            "avoid": card.avoid,
        },
        "evidence": {
            "event_type": etype,
            "round_number": rnd,
            "phase": event.get("phase"),
            "target_id": data.get("target_id"),
            "check_result": check_result,
            "event_message_excerpt": str(event.get("message", ""))[:200],
            "belief_context": belief_summary.to_evidence() if belief_summary else None,
            "scores": {"intention": None, "benefit": None},
        },
        "rationale": (
            f"[生成规则: {candidate.rule.rule_id}] "
            f"第{rnd}轮 {etype}，目标已选定"
            + (f"，结果 {check_result}。" if check_result else "。")
        ),
    }


def build_role_skills(ctx: RunContext, camp_report: CampPersuasionReport) -> dict[str, Any]:
    """构建 role_skills.json；仅包含通过生成规则的条目。"""
    candidates = collect_skill_generation_candidates(ctx, camp_report)
    belief_index = BeliefRunIndex.from_run_dir(ctx.run_dir)
    skills = [
        _skill_from_candidate(candidate, ctx, rank=idx, belief_index=belief_index)
        for idx, candidate in enumerate(candidates, start=1)
    ]
    _apply_skill_adoption_rules(skills, winner_camp=ctx.winner_camp)

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
        "apply_policy": "merge_when_to_use_then_sparse_bump",
        "merge_policy": {
            "match_field": "when_to_use",
            "similarity_threshold": _WHEN_TO_USE_MATCH_THRESHOLD,
            "weight_delta_on_merge": _MERGE_WEIGHT_DELTA,
        },
    }


def _apply_skill_adoption_rules(
    skills: list[dict[str, Any]],
    *,
    winner_camp: str | None,
) -> None:
    for skill in skills:
        _apply_initial_outcome_weight(skill, winner_camp=winner_camp)
        _update_skill_status(skill)


def _apply_initial_outcome_weight(skill: dict[str, Any], *, winner_camp: str | None) -> None:
    camp = str(skill.get("camp") or "")
    if not winner_camp or not camp:
        return
    if camp == winner_camp:
        skill["weight"] = round(float(skill.get("weight") or 1.0) + _WINNING_SKILL_WEIGHT_DELTA, 2)
        skill["win_count"] = int(skill.get("win_count") or 0) + 1
    else:
        skill["weight"] = round(
            max(0.1, float(skill.get("weight") or 1.0) + _LOSING_SKILL_WEIGHT_DELTA),
            2,
        )


def _update_skill_status(skill: dict[str, Any]) -> None:
    current = str(skill.get("status") or "draft")
    weight = float(skill.get("weight") or 1.0)
    if current == "skipped":
        return
    if weight >= _ACTIVATE_WEIGHT_THRESHOLD:
        skill["status"] = "active"
        return
    if current == "active" and weight <= _DEPRECATE_WEIGHT_THRESHOLD:
        skill["status"] = "deprecated"
        return
    if current not in {"draft", "active", "deprecated"}:
        skill["status"] = "draft"


def _build_skipped_summary(
    ctx: RunContext, camp_report: CampPersuasionReport, candidates: list[SkillGenerationCandidate]
) -> list[dict[str, Any]]:
    """记录本局有玩家但未生成 Skill 的身份（仅 JSON 摘要，不写 MD）。"""
    from llm_werewolf.game_runtime.prompts.manager import PromptManager
    from llm_werewolf.evaluation.post_game.skill_generation.skill_generation_rules import (
        evaluate_persuasion_speech,
    )

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


def is_eligible_for_agent_library(skill: dict[str, Any]) -> bool:
    """Gate auto-join into shared agent_team/skills (quality + trusted source_run)."""
    if skill.get("status") == "skipped":
        return False
    quality_gate = skill.get("quality_gate") or {}
    if not quality_gate.get("passed"):
        return False
    return is_trusted_source_run(str(skill.get("source_run") or ""))


def _when_to_use_from_skill(skill: dict[str, Any]) -> str:
    card = skill.get("skill_card") or {}
    return str(card.get("when_to_use") or "").strip()


def _load_existing_skills_for_merge(
    role_key: str,
    skill_version: str,
    *,
    agent_skills_root: Path,
) -> list[dict[str, Any]]:
    from llm_werewolf.agent_team.skill_support.skill_markdown import extract_when_to_use, read_skill_markdown

    role_dir = agent_skills_root / role_key / skill_version
    if not role_dir.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(role_dir.glob("*.md")):
        meta, body = read_skill_markdown(path)
        when_to_use = str(meta.get("when_to_use") or extract_when_to_use(body) or "").strip()
        items.append({
            "skill_id": str(meta.get("skill_id") or path.stem),
            "path": path,
            "when_to_use": when_to_use,
        })
    return items


def find_matching_library_skill(
    candidate: dict[str, Any],
    existing_items: list[dict[str, Any]],
    *,
    threshold: float = _WHEN_TO_USE_MATCH_THRESHOLD,
) -> dict[str, Any] | None:
    """Match a candidate skill to an existing library card by when_to_use similarity."""
    from llm_werewolf.agent_team.memory.semantic_matching import similarity

    when = _when_to_use_from_skill(candidate)
    if not when:
        return None
    best: dict[str, Any] | None = None
    best_score = 0.0
    for item in existing_items:
        existing_when = str(item.get("when_to_use") or "").strip()
        if not existing_when:
            continue
        score = similarity(when, existing_when)
        if score >= threshold and score > best_score:
            best = item
            best_score = score
    return best


def _merge_markdown_section(body: str, heading: str, incoming: str, merge_fn) -> str:
    if not incoming:
        return body
    if heading not in body:
        return f"{body.rstrip()}\n\n{heading}\n{incoming}\n"
    idx = body.index(heading)
    after = body[idx + len(heading) :]
    next_heading = after.find("\n## ")
    if next_heading == -1:
        section_text = after.strip()
        tail = ""
    else:
        section_text = after[:next_heading].strip()
        tail = after[next_heading:]
    merged = merge_fn(section_text, incoming) if section_text else incoming
    return body[:idx] + heading + "\n" + merged + "\n" + tail


def merge_candidate_into_existing_skill(
    existing: dict[str, Any],
    candidate: dict[str, Any],
    *,
    target_dir: Path,
    weight_delta: float = _MERGE_WEIGHT_DELTA,
) -> Path:
    """Rewrite an existing library skill and bump its weight when scenarios match."""
    from llm_werewolf.agent_team.memory.semantic_memory import clamp_weight
    from llm_werewolf.agent_team.memory.semantic_matching import merge_card_contents
    from llm_werewolf.agent_team.skill_support.skill_markdown import (
        read_skill_markdown,
        render_frontmatter_markdown,
    )

    source_path = Path(existing["path"])
    path = target_dir / source_path.name
    if not path.is_file() and source_path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    meta, body = read_skill_markdown(path)
    old_weight = float(meta.get("weight", 1.0))
    meta["weight"] = f"{clamp_weight(old_weight + weight_delta):.2f}"
    meta["use_count"] = str(int(meta.get("use_count", 0) or 0) + 1)
    meta["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if candidate.get("source_run"):
        meta["source_run"] = str(candidate["source_run"])

    card = candidate.get("skill_card") or {}
    body = _merge_markdown_section(
        body,
        "## 公开行为",
        str(card.get("public_behavior") or "").strip(),
        merge_card_contents,
    )
    body = _merge_markdown_section(
        body,
        "## 避免",
        str(card.get("avoid") or "").strip(),
        merge_card_contents,
    )
    rationale = str(candidate.get("rationale") or "").strip()
    if rationale:
        body = _merge_markdown_section(body, "## 提取依据", rationale, merge_card_contents)

    path.write_text(render_frontmatter_markdown(meta, body), encoding="utf-8")
    return path


def _copy_skills_to_new_version(
    role_key: str,
    *,
    base_version: str,
    new_version: str,
    agent_skills_root: Path,
) -> None:
    source_dir = agent_skills_root / role_key / base_version
    target_dir = agent_skills_root / role_key / new_version
    target_dir.mkdir(parents=True, exist_ok=True)
    if not source_dir.is_dir():
        return
    for path in source_dir.glob("*.md"):
        target_path = target_dir / path.name
        if not target_path.is_file():
            target_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def write_skill_markdown_files(
    skills: list[dict[str, Any]], *, run_skills_dir: Path, agent_skills_root: Path | None = None
) -> list[str]:
    """写入 run 目录下的 Skill MD；可选将通过门控的 Skill 双写 agent_team/skills/<role>/<version>/。"""
    from llm_werewolf.agent_team.skill_support import skill_loader
    from llm_werewolf.strategy.role_version_manifest import get_active_manifest, set_active_manifest

    written: list[str] = []
    merges_by_role: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    new_by_role: dict[str, list[dict[str, Any]]] = {}

    manifest = get_active_manifest()
    if agent_skills_root is not None:
        for skill in skills:
            if skill.get("status") == "skipped":
                continue
            if not is_eligible_for_agent_library(skill):
                continue
            role_key = str(skill.get("prompt_role_key") or "villager")
            current_version = manifest.skill_version_for(role_key)
            existing = _load_existing_skills_for_merge(
                role_key,
                current_version,
                agent_skills_root=agent_skills_root,
            )
            match = find_matching_library_skill(skill, existing)
            if match is not None:
                merges_by_role.setdefault(role_key, []).append((match, skill))
                skill["library_action"] = "merged"
                skill["merged_into_skill_id"] = match["skill_id"]
                skill["merge_weight_delta"] = _MERGE_WEIGHT_DELTA
            else:
                new_by_role.setdefault(role_key, []).append(skill)
                skill["library_action"] = "created"

    role_new_versions: dict[str, str] = {}
    library_roles = set(new_by_role) | set(merges_by_role)
    for role_key in sorted(library_roles):
        new_skills = new_by_role.get(role_key, [])
        merge_pairs = merges_by_role.get(role_key, [])
        if new_skills:
            current_version = manifest.skill_version_for(role_key)
            new_version = skill_loader.next_skill_version(role_key, current_version)
            _copy_skills_to_new_version(
                role_key,
                base_version=current_version,
                new_version=new_version,
                agent_skills_root=agent_skills_root,  # type: ignore[arg-type]
            )
            role_new_versions[role_key] = new_version
            target_version = new_version
        else:
            target_version = manifest.skill_version_for(role_key)

        role_dir = agent_skills_root / role_key / target_version  # type: ignore[operator]
        for existing, candidate in merge_pairs:
            agent_path = merge_candidate_into_existing_skill(
                existing,
                candidate,
                target_dir=role_dir,
            )
            candidate["agent_skill_path"] = str(agent_path)
            candidate["skill_version"] = target_version
            written.append(
                f"agent_team/skills/{role_key}/{target_version}/{agent_path.name}"
            )

        for skill in new_skills:
            skill_id = str(skill.get("skill_id") or "skill")
            filename = f"{skill_id}.md"
            body = render_skill_markdown(skill)
            agent_path = role_dir / filename
            agent_path.write_text(body, encoding="utf-8")
            skill["agent_skill_path"] = str(agent_path)
            skill["skill_version"] = target_version
            written.append(f"agent_team/skills/{role_key}/{target_version}/{filename}")

    if role_new_versions:
        updated = manifest
        for role_key, version in role_new_versions.items():
            updated = updated.with_skill_version(role_key, version)
        set_active_manifest(updated)
        skill_loader.list_role_skill_files.cache_clear()
    elif merges_by_role:
        skill_loader.list_role_skill_files.cache_clear()

    for skill in skills:
        if skill.get("status") == "skipped":
            continue
        skill_id = str(skill.get("skill_id") or "skill")
        filename = f"{skill_id}.md"
        body = render_skill_markdown(skill)

        run_path = run_skills_dir / filename
        run_skills_dir.mkdir(parents=True, exist_ok=True)
        run_path.write_text(body, encoding="utf-8")
        written.append(f"skills/{filename}")
        skill["md_path"] = str(run_path)

    return written


def write_role_skills_artifacts(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    agent_skills_root: Path | None = None,
    write_agent_library: bool = True,
) -> Path:
    """写出 role_skills.json 与 Skill MD（默认同步门控通过的 Skill 到 agent 库）。"""
    if agent_skills_root is None:
        from llm_werewolf.agent_team.skill_support.skill_loader import (
            agent_skills_root as default_root,
        )

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
