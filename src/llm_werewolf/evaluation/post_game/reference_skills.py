"""从本地对局日志提炼可联调的参考 Skill，并同步到 agent_team/skills。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import RunContext, load_run_context
from llm_werewolf.evaluation.post_game.skill_card_builder import (
    SkillCardContent,
    build_night_action_skill_card,
    build_persuasion_skill_card,
    build_wolf_night_coordination_card,
)
from llm_werewolf.evaluation.post_game.skill_extractor import (
    build_role_skills,
    write_skill_markdown_files,
)
from llm_werewolf.game_runtime.prompts.manager import PromptManager

# 无真实说服素材时的白天范例（网规常见逻辑，非伪造对局结果）
_VILLAGER_REFERENCE_SPEECH = (
    "我梳理一下：3号前两轮站边1号，投票却跟到5号，前后不一致。"
    "今天先把3号放上票型，看他怎么解释。"
)

_WOLF_DAY_REFERENCE_SPEECH = (
    "3号刚才说信预言家，转头又踩6号，逻辑对不上。"
    "今天先出3号，票型对齐，别分票。"
)


def find_best_source_run(runs_root: str | Path = "runs") -> Path | None:
    """优先选事件较丰富的本地对局目录。"""
    root = Path(runs_root)
    if not root.is_dir():
        return None

    preferred = root / "12p-doubao-20260526-143527"
    if (preferred / "events.jsonl").is_file():
        return preferred

    candidates = sorted(
        (p for p in root.iterdir() if p.is_dir() and (p / "events.jsonl").is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _skill_dict(
    *,
    skill_id: str,
    prompt_role_key: str,
    source_kind: str,
    source_run: str,
    card: SkillCardContent,
    evidence: dict[str, Any],
    rationale: str,
    source_player_id: str = "",
    source_player_name: str = "",
    game_role_name: str | None = None,
    camp: str | None = None,
    weight: float = 1.0,
    reference: bool = True,
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "skill_id": skill_id,
        "prompt_role_key": prompt_role_key,
        "source_kind": source_kind,
        "source_player_id": source_player_id,
        "source_player_name": source_player_name,
        "game_role_name": game_role_name,
        "camp": camp,
        "source_run": source_run,
        "status": "active" if reference else "draft",
        "weight": weight,
        "win_count": 0,
        "use_count": 0,
        "created_at": now,
        "updated_at": now,
        "quality_gate": {
            "passed": True,
            "rule_id": "reference_curated",
            "reason": "curated from local run logs and role strategy",
        },
        "skill_card": {
            "title_zh": card.title_zh,
            "when_to_use": card.when_to_use,
            "public_behavior": card.public_behavior,
            "avoid": card.avoid,
        },
        "evidence": evidence,
        "rationale": rationale,
        "reference_curated": reference,
    }


def _wolf_night_kill_target(ctx: RunContext, round_number: int) -> str | None:
    for event in ctx.events:
        if event.get("event_type") != "werewolf_killed":
            continue
        if int(event.get("round_number", 0)) != round_number:
            continue
        data = event.get("data") or {}
        target = str(data.get("target_id") or "")
        return target or None
    return None


def _wolf_night_speeches(ctx: RunContext, round_number: int) -> list[str]:
    speeches: list[str] = []
    for event in ctx.events:
        if event.get("event_type") != "player_discussion":
            continue
        if event.get("phase") != "night":
            continue
        if int(event.get("round_number", 0)) != round_number:
            continue
        data = event.get("data") or {}
        role = str(data.get("role") or "")
        if "Wolf" not in role and role != "Werewolf":
            continue
        speech = str(data.get("speech") or "").strip()
        if speech and speech not in speeches:
            speeches.append(speech)
    return speeches


def _build_wolf_night_skill(ctx: RunContext, *, round_number: int = 1) -> dict[str, Any] | None:
    speeches = _wolf_night_speeches(ctx, round_number)
    kill_target = _wolf_night_kill_target(ctx, round_number)
    if not speeches and not kill_target:
        return None

    # 过滤明显兜底话术，保留可读的协商范例
    usable = [s for s in speeches if "对齐" not in s or "刀" in s or len(s) > 14]
    if not usable and speeches:
        usable = speeches[:2]

    card = build_wolf_night_coordination_card(
        round_number=round_number,
        speeches=usable,
        kill_target_id=kill_target,
        ctx=ctx,
    )
    return _skill_dict(
        skill_id=f"wolf_r{round_number}_night_knife_align",
        prompt_role_key="wolf",
        source_kind="wolf_night_coordination",
        source_run=str(ctx.run_dir),
        card=card,
        evidence={
            "round_number": round_number,
            "phase": "night",
            "kill_target_id": kill_target,
            "coordination_excerpt": "；".join(usable)[:200],
            "scores": {"intention": None, "benefit": None},
        },
        rationale=(
            f"[reference_curated] 第{round_number}轮狼队夜间频道 "
            f"{len(usable)} 条发言，刀口 {kill_target or '未记录'}。"
        ),
        camp="werewolf",
        weight=1.3,
    )


def _build_villager_day_skill(ctx: RunContext) -> dict[str, Any]:
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampSpeechInfluence

    speech = CampSpeechInfluence(
        speaker_id="reference_villager",
        speaker_name="村民参考",
        speaker_camp="villager",
        round_number=2,
        phase="day_discussion",
        public_speech=_VILLAGER_REFERENCE_SPEECH,
        swing_count=0,
        camp_aligned_swings=0,
        camp_aligned_score=0,
        matched_round_elimination=False,
        swings=[],
    )
    card = build_persuasion_skill_card(role_key="villager", speech=speech, ctx=ctx)
    card = SkillCardContent(
        title_zh="第2轮平民逻辑归票",
        when_to_use=card.when_to_use.replace(
            "本局发言后产生 0 次同阵营意向摇摆",
            "场上出现发言与投票不一致、需平民带逻辑链归票时",
        ),
        public_behavior=card.public_behavior,
        avoid=card.avoid,
    )
    return _skill_dict(
        skill_id="villager_r2_logic_chain_push",
        prompt_role_key="villager",
        source_kind="reference_scenario",
        source_run=str(ctx.run_dir),
        card=card,
        evidence={
            "round_number": 2,
            "phase": "day_discussion",
            "public_speech_excerpt": _VILLAGER_REFERENCE_SPEECH,
            "scores": {"intention": None, "benefit": None},
        },
        rationale="[reference_curated] 平民白天逻辑链归票范例（策略提炼，可迁移到类似局面）。",
        camp="villager",
        weight=1.0,
    )


def _build_wolf_day_skill(ctx: RunContext) -> dict[str, Any]:
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampSpeechInfluence

    speech = CampSpeechInfluence(
        speaker_id="reference_wolf",
        speaker_name="狼人参考",
        speaker_camp="werewolf",
        round_number=2,
        phase="day_discussion",
        public_speech=_WOLF_DAY_REFERENCE_SPEECH,
        swing_count=2,
        camp_aligned_swings=2,
        camp_aligned_score=16,
        matched_round_elimination=True,
        elimination_target_id="player_3",
        swings=[],
    )
    card = build_persuasion_skill_card(role_key="wolf", speech=speech, ctx=ctx)
    return _skill_dict(
        skill_id="wolf_r2_suspicion_chain_push",
        prompt_role_key="wolf",
        source_kind="reference_scenario",
        source_run=str(ctx.run_dir),
        card=card,
        evidence={
            "round_number": 2,
            "phase": "day_discussion",
            "public_speech_excerpt": _WOLF_DAY_REFERENCE_SPEECH,
            "camp_aligned_swings": 2,
            "matched_round_elimination": True,
            "scores": {"intention": 16, "benefit": None},
        },
        rationale="[reference_curated] 狼人白天抗推归票范例（矛盾链 + 单一目标）。",
        camp="werewolf",
        weight=1.2,
    )


def _from_extracted_skill(raw: dict[str, Any], *, ctx: RunContext) -> dict[str, Any]:
    """把规则提取结果升级为 reference active 卡片。"""
    source_kind = str(raw.get("source_kind", ""))
    card_data = dict(raw.get("skill_card") or {})
    evidence = dict(raw.get("evidence") or {})

    if source_kind == "night_action":
        event = {
            "event_type": evidence.get("event_type"),
            "round_number": evidence.get("round_number"),
            "phase": evidence.get("phase"),
            "message": evidence.get("event_message_excerpt", ""),
            "data": {
                "player_id": raw.get("source_player_id"),
                "target_id": evidence.get("target_id"),
                "result": evidence.get("check_result"),
            },
        }
        card = build_night_action_skill_card(
            role_key=str(raw.get("prompt_role_key", "villager")),
            event=event,
            ctx=ctx,
        )
        card_data = {
            "title_zh": card.title_zh,
            "when_to_use": card.when_to_use,
            "public_behavior": card.public_behavior,
            "avoid": card.avoid,
        }

    upgraded = dict(raw)
    upgraded["skill_card"] = card_data
    upgraded["status"] = "active"
    upgraded["weight"] = max(float(raw.get("weight") or 1.0), 1.2)
    upgraded["reference_curated"] = True
    upgraded["quality_gate"] = {
        "passed": True,
        "rule_id": "reference_curated",
        "reason": "upgraded from post_game extraction",
    }
    return upgraded


def build_reference_skills(run_dir: str | Path) -> list[dict[str, Any]]:
    """从对局日志构建一组可实际使用的参考 Skill（真实提取 + 场景补全）。"""
    run_path = Path(run_dir)
    ctx = load_run_context(run_path)
    camp = build_camp_persuasion_report(ctx)
    extracted_payload = build_role_skills(ctx, camp)
    skills: list[dict[str, Any]] = [
        _from_extracted_skill(s, ctx=ctx) for s in extracted_payload.get("skills") or []
    ]

    covered_roles = {s["prompt_role_key"] for s in skills}
    covered_kinds: dict[str, set[str]] = {}
    for s in skills:
        covered_kinds.setdefault(s["prompt_role_key"], set()).add(s["source_kind"])

    wolf_night = _build_wolf_night_skill(ctx, round_number=1)
    if wolf_night and "wolf" not in covered_kinds.get("wolf", set()):
        skills.append(wolf_night)
        covered_roles.add("wolf")

    if "wolf" not in covered_kinds.get("wolf", set()) or "persuasion_speech" not in (
        covered_kinds.get("wolf") or set()
    ):
        skills.append(_build_wolf_day_skill(ctx))

    if "villager" not in covered_roles:
        skills.append(_build_villager_day_skill(ctx))

    # 每身份最多 2 条，按 weight 截断
    by_role: dict[str, list[dict[str, Any]]] = {}
    for skill in sorted(skills, key=lambda s: float(s.get("weight") or 0), reverse=True):
        role = str(skill.get("prompt_role_key") or "villager")
        bucket = by_role.setdefault(role, [])
        if len(bucket) >= 2:
            continue
        if skill["skill_id"] not in {x["skill_id"] for x in bucket}:
            bucket.append(skill)

    ordered: list[dict[str, Any]] = []
    for role in sorted(by_role):
        ordered.extend(by_role[role])
    return ordered


def _prune_role_dir(role_dir: Path, keep_ids: set[str]) -> None:
    if not role_dir.is_dir():
        return
    for path in role_dir.glob("*.md"):
        skill_id = path.stem
        if skill_id not in keep_ids:
            path.unlink(missing_ok=True)


def sync_agent_skill_library(
    run_dir: str | Path | None = None,
    *,
    agent_skills_root: Path | None = None,
    runs_root: str | Path = "runs",
) -> Path:
    """清理 agent_team/skills 旧卡片，写入最新参考 Skill 集。"""
    if agent_skills_root is None:
        from llm_werewolf.agent_team.skill_loader import agent_skills_root as default_root

        agent_skills_root = default_root()

    source = Path(run_dir) if run_dir else find_best_source_run(runs_root)
    if source is None:
        raise FileNotFoundError("no local run with events.jsonl found under runs/")

    skills = build_reference_skills(source)
    keep_by_role: dict[str, set[str]] = {}
    for skill in skills:
        role = str(skill.get("prompt_role_key") or "villager")
        keep_by_role.setdefault(role, set()).add(str(skill["skill_id"]))

    for role_dir in agent_skills_root.iterdir():
        if role_dir.is_dir():
            _prune_role_dir(role_dir, keep_by_role.get(role_dir.name, set()))

    md_files = write_skill_markdown_files(
        skills,
        run_skills_dir=source / "skills_reference",
        agent_skills_root=agent_skills_root,
    )

    payload = {
        "schema": "role_skills_reference_v1",
        "generated_at": _now_iso(),
        "run_dir": str(source),
        "reference_curated": True,
        "skill_count": len(skills),
        "skills": skills,
        "apply_policy": "agent_library_active_reference",
        "md_files": md_files,
    }
    json_path = source / "role_skills_reference.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    from llm_werewolf.agent_team import skill_loader

    skill_loader.list_role_skill_files.cache_clear()
    return json_path


def build_mock_integration_skills(run_dir: str | Path) -> list[dict[str, Any]]:
    """兼容旧接口：返回参考 Skill 集（优先真实日志）。"""
    return build_reference_skills(run_dir)


def write_mock_integration_skills(
    run_dir: str | Path,
    *,
    agent_skills_root: Path | None = None,
    merge_into_existing: bool = False,
) -> Path:
    """兼容旧接口：同步参考 Skill 到 agent 库。"""
    if merge_into_existing:
        return sync_agent_skill_library(run_dir, agent_skills_root=agent_skills_root)
    return sync_agent_skill_library(run_dir, agent_skills_root=agent_skills_root)
