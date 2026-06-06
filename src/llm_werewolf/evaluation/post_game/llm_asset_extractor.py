"""从 LLM 复盘报告提取 Prompt 提案与 Skill，并与规则层草案合并。"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

from pydantic import ValidationError
from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.agent_team.agents.factory import create_react_agent
from llm_werewolf.agent_team.agents.agentscope_agent import (
    _extract_structured_payload_from_content,
)
from llm_werewolf.agent_team.invocation.serial_calls import run_serial_agent_call
from llm_werewolf.agent_team.invocation.structured_invoke import (
    unwrap_structured_metadata,
    generate_response_instruction,
)
from llm_werewolf.evaluation.post_game.assets_prompt_builder import build_assets_extraction_prompt
from llm_werewolf.evaluation.post_game.skill_generation.skill_belief_support import (
    attach_belief_context_to_skill,
    belief_index_for_ctx,
    compose_when_to_use,
    find_matching_skill_by_when,
    resolve_belief_trigger,
    resolve_wolf_camp_trigger,
)
from llm_werewolf.evaluation.post_game.eval_agent import _load_analyst_config, _parse_json_response
from llm_werewolf.evaluation.registry.post_game_prompt_registry import load_assets_prompt_bundle
from llm_werewolf.game_runtime.support.env import load_project_dotenv
from llm_werewolf.strategy.contracts.evaluation_outputs import (
    LlmPromptProposalItem,
    LlmSkillItem,
    PostGameAssetExtractionDecision,
)

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext

_LLM_KIND_TO_ACTION = {
    "positive_persuasion": "update_rule",
    "bad_case_rule": "add_forbidden_rule",
    "mvp_golden_quote": "promote_quote_to_example",
    "llm_coaching": "append_guidance",
    "mvp_strategy_highlight": "update_rule",
}


def _parse_asset_decision(response_msg: Any) -> PostGameAssetExtractionDecision | None:
    metadata = unwrap_structured_metadata(getattr(response_msg, "metadata", None))
    if not metadata:
        metadata = _extract_structured_payload_from_content(
            getattr(response_msg, "content", None)
        )
    if metadata:
        try:
            return PostGameAssetExtractionDecision.model_validate(metadata)
        except ValidationError:
            pass
    content = getattr(response_msg, "content", None)
    if isinstance(content, str) and content.strip():
        try:
            return PostGameAssetExtractionDecision.model_validate(_parse_json_response(content))
        except (json.JSONDecodeError, ValidationError):
            return None
    return None


def _slug(text: str, *, max_len: int = 32) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len] or "skill"


async def run_llm_asset_extraction(
    ctx: RunContext,
    *,
    llm_analysis: dict[str, Any] | None,
    rule_proposals: list[dict[str, Any]],
    rule_skills: list[dict[str, Any]],
    bad_cases: list[dict[str, Any]],
    mvp_payload: dict[str, Any] | None = None,
    config_path: Path | None = None,
    assets_prompt_version: str | None = None,
) -> dict[str, Any]:
    """调用 Evaluation Analyst 从复盘材料提取结构化 Prompt/Skill 资产。"""
    load_project_dotenv()
    bundle = load_assets_prompt_bundle(assets_prompt_version)
    analyst_config = _load_analyst_config(config_path)

    base_meta = {
        "schema": "llm_assets_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "assets_prompt_version": bundle.version,
        "prompt_proposals": [],
        "skills": [],
        "extraction_notes": "",
    }

    if analyst_config is None:
        return {**base_meta, "mode": "skipped", "reason": "no_api_config_or_key"}

    user_body = build_assets_extraction_prompt(
        bundle=bundle,
        ctx=ctx,
        ctx_winner_camp=ctx.winner_camp,
        ctx_prompt_version=ctx.prompt_version,
        llm_analysis=llm_analysis,
        rule_proposals=rule_proposals,
        rule_skills=rule_skills,
        bad_cases=bad_cases,
        mvp_payload=mvp_payload,
    )

    try:
        react_agent = create_react_agent(
            analyst_config,
            agent_name="AssetExtractor",
            sys_prompt=bundle.system_prompt,
        )
        user_prompt = (
            f"{user_body}\n\n{bundle.json_reminder}\n\n"
            f"{generate_response_instruction('PostGameAssetExtractionDecision')}"
        )
        input_msg = AgentScopeMsg(name="Moderator", content=user_prompt, role="user")
        response_msg = await run_serial_agent_call(
            lambda: react_agent(
                input_msg,
                structured_model=PostGameAssetExtractionDecision,
            )
        )
        parsed = _parse_asset_decision(response_msg)
        if parsed is None:
            plain = f"{user_prompt}\n\n{bundle.plain_json_fallback}"
            plain_msg = AgentScopeMsg(name="Moderator", content=plain, role="user")
            response_msg = await run_serial_agent_call(lambda: react_agent(plain_msg))
            parsed = _parse_asset_decision(response_msg)
        if parsed is None:
            return {
                **base_meta,
                "mode": "failed",
                "reason": "empty asset extraction response",
            }
        return {
            **base_meta,
            "mode": "llm",
            **parsed.model_dump(),
        }
    except Exception as exc:
        return {**base_meta, "mode": "failed", "reason": str(exc)}


def write_llm_assets(ctx: RunContext, payload: dict[str, Any]) -> Path:
    path = ctx.run_dir / "llm_assets.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def llm_item_to_proposal_dict(
    item: LlmPromptProposalItem | dict[str, Any],
    ctx: RunContext,
    *,
    rank: int,
) -> dict[str, Any]:
    row = item if isinstance(item, dict) else item.model_dump()
    role_key = str(row.get("prompt_role_key") or "villager")
    kind = str(row.get("kind") or "llm_coaching")
    action = _LLM_KIND_TO_ACTION.get(kind, "append_guidance")
    text = str(row.get("suggested_patch_text_zh") or "").strip()
    proposal_id = f"llm_{kind}_{rank}_{role_key}"
    return {
        "proposal_id": proposal_id,
        "prompt_role_key": role_key,
        "target_variable": f"{ctx.prompt_version}.role.{role_key}",
        "prompt_version_base": ctx.prompt_version,
        "status": "draft",
        "kind": kind,
        "priority": rank,
        "confidence_score": float(row.get("confidence_score") or 0.8),
        "target_layer": str(row.get("target_layer") or "prompt_rule"),
        "evidence_scope": "llm_replay_extraction",
        "source": "llm",
        "suggested_patch": {
            "section": "vote_closing" if kind == "positive_persuasion" else "guidance",
            "target_field": "phase_strategies.vote_closing"
            if kind == "positive_persuasion"
            else "coaching_rules",
            "action": action,
            "text_zh": text,
        },
        "evidence": {
            "source": "llm_assets.json",
            "excerpt": str(row.get("evidence_excerpt") or text)[:280],
            "round_number": row.get("evidence_round"),
            "llm_rationale": str(row.get("rationale") or ""),
        },
        "rationale": str(row.get("rationale") or "LLM 从复盘报告提取的可落地 Prompt 补丁。"),
    }


def merge_llm_proposals(
    rule_payload: dict[str, Any],
    llm_assets: dict[str, Any] | None,
    *,
    ctx: RunContext,
) -> dict[str, Any]:
    """规则提案 + LLM 提取合并；模板化正向提案可被 LLM 同角色条目替代。"""
    proposals = list(rule_payload.get("proposals") or [])
    for prop in proposals:
        prop.setdefault("source", "rule")

    if not llm_assets or llm_assets.get("mode") != "llm":
        rule_payload["llm_merge"] = {"applied": False, "reason": llm_assets.get("mode") if llm_assets else "none"}
        return rule_payload

    llm_items = llm_assets.get("prompt_proposals") or []
    llm_roles_replaced: set[str] = set()
    rank_base = len(proposals) + 1

    for idx, raw in enumerate(llm_items):
        item = (
            raw
            if isinstance(raw, LlmPromptProposalItem)
            else LlmPromptProposalItem.model_validate(raw)
        )
        if not item.suggested_patch_text_zh.strip():
            continue
        role = item.prompt_role_key
        if item.kind == "positive_persuasion" and role not in llm_roles_replaced:
            proposals = [
                p
                for p in proposals
                if not (
                    p.get("source") == "rule"
                    and p.get("prompt_role_key") == role
                    and p.get("kind") == "positive_persuasion"
                    and "参考本局有效发言模式" in str((p.get("suggested_patch") or {}).get("text_zh") or "")
                )
            ]
            llm_roles_replaced.add(role)
        proposals.append(llm_item_to_proposal_dict(item, ctx, rank=rank_base + idx))

    rule_payload["proposals"] = proposals
    rule_payload["proposal_count"] = len(proposals)
    rule_payload["llm_merge"] = {
        "applied": True,
        "llm_proposal_count": len(llm_items),
        "extraction_notes": llm_assets.get("extraction_notes") or "",
    }
    return rule_payload


def _finalize_llm_skill_fields(
    item: LlmSkillItem,
    ctx: RunContext,
    *,
    belief_index: Any,
) -> tuple[str, str, str, dict[str, Any] | None]:
    player_id = str(item.source_player_id or "").strip()
    rnd = item.evidence_round
    belief_trigger = str(item.belief_trigger_zh or "").strip()
    wolf_trigger = str(item.wolf_camp_trigger_zh or "").strip()
    if not wolf_trigger and player_id and rnd is not None:
        wolf_trigger = resolve_wolf_camp_trigger(
            ctx, observer_id=player_id, round_number=rnd, index=belief_index
        )
    belief_evidence = None
    if player_id and rnd is not None:
        belief_evidence = resolve_belief_trigger(
            ctx,
            observer_id=player_id,
            round_number=rnd,
            phase=item.evidence_phase or "day_discussion",
            index=belief_index,
        )
        if belief_evidence and not belief_trigger:
            belief_trigger = str(belief_evidence.get("when_clause") or "").strip()
    full_when = compose_when_to_use(
        scene=item.when_to_use,
        belief_trigger=belief_trigger,
        wolf_camp_trigger=wolf_trigger,
        prompt_role_key=item.prompt_role_key,
    )
    return full_when, belief_trigger, wolf_trigger, belief_evidence


def llm_item_to_skill_dict(
    item: LlmSkillItem | dict[str, Any],
    ctx: RunContext,
    *,
    rank: int,
    belief_index: Any = None,
) -> dict[str, Any]:
    model = item if isinstance(item, LlmSkillItem) else LlmSkillItem.model_validate(item)
    idx = belief_index or belief_index_for_ctx(ctx)
    role_key = model.prompt_role_key
    title = model.title_zh or f"{role_key} 策略"
    skill_id = f"llm_{role_key}_{_slug(title)}_{rank}"
    player_id = str(model.source_player_id or "").strip()
    entry = ctx.roster.get(player_id) if player_id else None
    camp = entry.camp if entry else None
    full_when, belief_trigger, wolf_trigger, belief_evidence = _finalize_llm_skill_fields(
        model, ctx, belief_index=idx
    )
    skill = {
        "skill_id": skill_id,
        "prompt_role_key": role_key,
        "source_player_id": player_id or None,
        "source_player_name": entry.player_name if entry else None,
        "camp": camp,
        "status": "draft",
        "source": "llm",
        "quality_gate": {"passed": model.quality_passed},
        "skill_card": {
            "title_zh": title,
            "when_to_use": full_when,
            "scene_when_to_use": model.when_to_use,
            "public_behavior": model.public_behavior,
            "avoid": model.avoid,
        },
        "evidence": {
            "source": "llm_assets.json",
            "llm_rationale": model.rationale,
            "evidence_round": model.evidence_round,
            "evidence_phase": model.evidence_phase,
        },
        "rationale": model.rationale or "LLM 从复盘报告提取的 Skill。",
        "weight": 1.0,
        "win_count": 0,
        "use_count": 0,
    }
    attach_belief_context_to_skill(
        skill,
        belief_evidence,
        wolf_camp_trigger=wolf_trigger,
    )
    if belief_trigger and not (belief_evidence or {}).get("when_clause"):
        skill["evidence"]["belief_trigger_zh"] = belief_trigger
    return skill


def _apply_llm_skill_to_target(
    target: dict[str, Any],
    item: LlmSkillItem,
    ctx: RunContext,
    *,
    belief_index: Any,
    match_score: float,
) -> None:
    full_when, _belief_trigger, wolf_trigger, belief_evidence = _finalize_llm_skill_fields(
        item, ctx, belief_index=belief_index
    )
    card = target.setdefault("skill_card", {})
    card["when_to_use"] = full_when
    card["scene_when_to_use"] = item.when_to_use
    card["title_zh"] = item.title_zh or card.get("title_zh") or target.get("skill_id")
    card["public_behavior"] = item.public_behavior
    if item.avoid:
        card["avoid"] = item.avoid
    target["source"] = "rule+llm"
    target["llm_rationale"] = item.rationale
    target["extraction_mode"] = "llm_enriched"
    target.setdefault("evidence", {})["llm_merge_score"] = round(match_score, 3)
    attach_belief_context_to_skill(target, belief_evidence, wolf_camp_trigger=wolf_trigger)


def merge_llm_skills(
    rule_payload: dict[str, Any],
    llm_assets: dict[str, Any] | None,
    *,
    ctx: RunContext,
) -> dict[str, Any]:
    """按「使用时机+作用」相似度合并：相同则重写，不同则新增 Skill。"""
    skills = list(rule_payload.get("skills") or [])
    for skill in skills:
        skill.setdefault("source", "rule")

    if not llm_assets or llm_assets.get("mode") != "llm":
        rule_payload["llm_merge"] = {"applied": False, "reason": llm_assets.get("mode") if llm_assets else "none"}
        return rule_payload

    belief_index = belief_index_for_ctx(ctx)
    llm_items = llm_assets.get("skills") or []
    added = 0
    enriched = 0
    merge_log: list[dict[str, Any]] = []

    for idx, raw in enumerate(llm_items):
        item = raw if isinstance(raw, LlmSkillItem) else LlmSkillItem.model_validate(raw)
        if not item.quality_passed:
            continue
        if not item.when_to_use.strip() or not item.public_behavior.strip():
            continue

        target, score = find_matching_skill_by_when(
            skills,
            prompt_role_key=item.prompt_role_key,
            scene_when=item.when_to_use,
        )
        if target is not None:
            _apply_llm_skill_to_target(
                target, item, ctx, belief_index=belief_index, match_score=score
            )
            enriched += 1
            merge_log.append({
                "action": "rewrite",
                "skill_id": target.get("skill_id"),
                "role": item.prompt_role_key,
                "match_score": round(score, 3),
            })
        else:
            new_skill = llm_item_to_skill_dict(
                item, ctx, rank=idx + 1, belief_index=belief_index
            )
            skills.append(new_skill)
            added += 1
            merge_log.append({
                "action": "create",
                "skill_id": new_skill.get("skill_id"),
                "role": item.prompt_role_key,
                "match_score": round(score, 3),
            })

    rule_payload["skills"] = skills
    rule_payload["skill_count"] = len([s for s in skills if s.get("status") != "skipped"])
    rule_payload["extraction_mode"] = "generation_rules+llm"
    rule_payload["llm_merge"] = {
        "applied": True,
        "enriched": enriched,
        "added": added,
        "merge_log": merge_log,
        "when_match_threshold": 0.78,
        "extraction_notes": llm_assets.get("extraction_notes") or "",
    }
    return rule_payload
