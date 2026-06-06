"""信念矩阵 / 狼队矩阵：Skill 触发条件提取与 when_to_use 匹配。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from llm_werewolf.agent_team.memory.semantic_matching import similarity
from llm_werewolf.evaluation.post_game.skill_generation.skill_card_builder import (
    BeliefRunIndex,
    build_belief_when_clause,
)

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext

_WOLF_PROMPT_ROLES = frozenset({"wolf", "wolf_king", "white_wolf", "blood_moon_apostle"})
_BELIEF_MARKER = "；信念矩阵触发："
_WOLF_MARKER = "；狼队矩阵触发："
_WHEN_MATCH_THRESHOLD = 0.78


def belief_rows_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 events.jsonl 的 belief_snapshot 事件展平为 beliefs.jsonl 行。"""
    rows: list[dict[str, Any]] = []
    for event in events:
        if str(event.get("event_type", "")) != "belief_snapshot":
            continue
        data = event.get("data") or {}
        for snapshot in data.get("snapshots") or []:
            if isinstance(snapshot, dict):
                rows.append(snapshot)
    return rows


def ensure_beliefs_jsonl(run_dir: str | Path, events: list[dict[str, Any]]) -> bool:
    """若 beliefs.jsonl 缺失，从 events 回写（供 Skill 信念索引）。"""
    path = Path(run_dir) / "beliefs.jsonl"
    if path.is_file() and path.stat().st_size > 0:
        return True
    rows = belief_rows_from_events(events)
    if not rows:
        return False
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return True


def belief_index_for_ctx(ctx: RunContext) -> BeliefRunIndex:
    ensure_beliefs_jsonl(ctx.run_dir, ctx.events)
    return BeliefRunIndex.from_run_dir(ctx.run_dir)


def scene_part_from_when(when_text: str) -> str:
    """提取场景部分，剥离矩阵触发后缀以便匹配「使用时机」。"""
    text = str(when_text or "").strip()
    for marker in (_BELIEF_MARKER, _WOLF_MARKER, "；信念分布（"):
        if marker in text:
            text = text.split(marker, 1)[0].strip()
    return text


def compose_when_to_use(
    *,
    scene: str,
    belief_trigger: str = "",
    wolf_camp_trigger: str = "",
    prompt_role_key: str,
) -> str:
    parts = [str(scene or "").strip()]
    role = str(prompt_role_key or "")
    if role in _WOLF_PROMPT_ROLES and wolf_camp_trigger.strip():
        parts.append(f"{_WOLF_MARKER}{wolf_camp_trigger.strip()}")
    elif belief_trigger.strip():
        parts.append(f"{_BELIEF_MARKER}{belief_trigger.strip()}")
    return "；".join(part for part in parts if part)


def find_matching_skill_by_when(
    skills: list[dict[str, Any]],
    *,
    prompt_role_key: str,
    scene_when: str,
    threshold: float = _WHEN_MATCH_THRESHOLD,
) -> tuple[dict[str, Any] | None, float]:
    """同角色下按使用时机相似度找可重写 Skill（非仅按角色）。"""
    scene = scene_part_from_when(scene_when).strip()
    if not scene:
        return None, 0.0
    best: dict[str, Any] | None = None
    best_score = 0.0
    for skill in skills:
        if str(skill.get("prompt_role_key") or "") != prompt_role_key:
            continue
        if skill.get("status") == "skipped":
            continue
        card = skill.get("skill_card") or {}
        existing_scene = scene_part_from_when(
            str(card.get("when_to_use") or card.get("when_to_use_zh") or "")
        )
        if not existing_scene:
            continue
        score = similarity(scene, existing_scene)
        if score > best_score:
            best_score = score
            best = skill
    if best is not None and best_score >= threshold:
        return best, best_score
    return None, best_score


def resolve_belief_trigger(
    ctx: RunContext,
    *,
    observer_id: str,
    round_number: int | None,
    phase: str = "day_discussion",
    index: BeliefRunIndex | None = None,
) -> dict[str, Any] | None:
    if not observer_id or round_number is None:
        return None
    idx = index or belief_index_for_ctx(ctx)
    snapshot = idx.find_persuasion_snapshot(
        observer_id=observer_id,
        round_number=round_number,
        phase=phase,
    )
    if snapshot is None:
        snapshot = idx.find_night_snapshot(observer_id=observer_id, round_number=round_number or 1)
    summary = build_belief_when_clause(snapshot)
    return summary.to_evidence() if summary else None


def resolve_wolf_camp_trigger(
    ctx: RunContext,
    *,
    observer_id: str,
    round_number: int | None,
    index: BeliefRunIndex | None = None,
) -> str:
    """从信念快照中的 wolf_camp_delta 或狼人 B1 队友结构提炼 W 矩阵触发描述。"""
    if not observer_id or round_number is None:
        return ""
    idx = index or belief_index_for_ctx(ctx)
    snapshot = idx.find_persuasion_snapshot(
        observer_id=observer_id,
        round_number=round_number,
        phase="day_discussion",
    )
    if snapshot is None:
        return ""
    delta = snapshot.get("wolf_camp_delta")
    if isinstance(delta, dict) and delta:
        parts = []
        if delta.get("god_role_intel"):
            parts.append("神职威胁雷达已更新")
        if delta.get("exposure_radar"):
            parts.append("队友暴露度可感知")
        if parts:
            return "；".join(parts)
    b1 = snapshot.get("first_order") or []
    teammate_hits = [
        row for row in b1
        if isinstance(row, dict) and float(row.get("wolf_probability", 0) or 0) >= 0.9
    ]
    if len(teammate_hits) >= 1:
        return "B1 已对队友座位高置信，适合统一刀口/白天抗推节奏"
    return ""


def attach_belief_context_to_skill(
    skill: dict[str, Any],
    belief_evidence: dict[str, Any] | None,
    *,
    wolf_camp_trigger: str = "",
) -> None:
    evidence = skill.setdefault("evidence", {})
    if belief_evidence:
        evidence["belief_context"] = belief_evidence
    if wolf_camp_trigger:
        evidence["wolf_camp_trigger"] = wolf_camp_trigger


def format_belief_excerpts_for_prompt(ctx: RunContext, *, limit: int = 8) -> list[str]:
    """为 LLM 资产提取提供信念矩阵摘要行。"""
    index = belief_index_for_ctx(ctx)
    lines: list[str] = []
    seen: set[str] = set()
    for row in reversed(index.rows):
        observer = str(row.get("observer_id") or "")
        rnd = int(row.get("round", 0) or 0)
        anchor = str(row.get("anchor") or "")
        key = f"{observer}:{rnd}:{anchor}"
        if key in seen:
            continue
        seen.add(key)
        summary = build_belief_when_clause(row)
        if summary is None:
            continue
        lines.append(
            f"- {observer} R{rnd}/{anchor}: {summary.when_clause} [pattern={summary.pattern}]"
        )
        if len(lines) >= limit:
            break
    return list(reversed(lines))
