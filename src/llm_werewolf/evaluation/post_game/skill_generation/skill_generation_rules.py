"""Skill 生成规则（Phase 2）：阵营感知门控 + 夜间结果筛选。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from dataclasses import field, dataclass

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp
from llm_werewolf.evaluation.post_game.skill_generation.skill_card_builder import (
    dedupe_skill_candidates,
)

if TYPE_CHECKING:
    from llm_werewolf.evaluation.post_game.camp_persuasion import (
        CampSpeechInfluence,
        CampPersuasionReport,
    )

MIN_PUBLIC_SPEECH_LEN = 8

NIGHT_ACTION_EVENT_TYPES = frozenset({
    "seer_checked",
    "witch_saved",
    "witch_poisoned",
    "guard_protected",
})

SkillSourceKind = Literal["persuasion_speech", "night_action"]


@dataclass(frozen=True)
class GenerationRuleResult:
    passed: bool
    rule_id: str
    reason: str


@dataclass
class SkillGenerationCandidate:
    source_kind: SkillSourceKind
    prompt_role_key: str
    player_id: str
    player_name: str
    game_role_name: str | None
    camp: str | None
    rule: GenerationRuleResult
    rank_score: int = 0
    speech: CampSpeechInfluence | None = None
    night_event: dict[str, Any] | None = field(default=None, repr=False)


@dataclass(frozen=True)
class SkippedCandidate:
    source_kind: str
    player_id: str
    player_name: str
    rule_id: str
    reason: str


def _role_key_for_player(ctx: RunContext, player_id: str) -> str:
    entry = ctx.roster.get(player_id)
    if entry and entry.role_name:
        return PromptManager.get_prompt_role_key(entry.role_name)
    return "villager"


def _elim_target_camp(speech: CampSpeechInfluence, ctx: RunContext) -> str | None:
    target_id = speech.elimination_target_id
    return target_id_to_camp(target_id, ctx.roster) if target_id else None


def evaluate_persuasion_speech(
    speech: CampSpeechInfluence, ctx: RunContext, *, swing_to_final_vote: int = 0
) -> GenerationRuleResult:
    """白天公开发言：阵营感知 + 推动有效放逐/归票。"""
    text = (speech.public_speech or "").strip()
    if len(text) < MIN_PUBLIC_SPEECH_LEN:
        return GenerationRuleResult(
            passed=False,
            rule_id="persuasion_speech",
            reason="insufficient_material: public_speech too short or empty",
        )

    elim_camp = _elim_target_camp(speech, ctx)
    speaker_camp = speech.speaker_camp

    if speaker_camp == Camp.WEREWOLF.value:
        if speech.matched_round_elimination and elim_camp == Camp.VILLAGER.value:
            return GenerationRuleResult(
                passed=True, rule_id="persuasion_speech", reason="wolf drove villager elimination"
            )
        return GenerationRuleResult(
            passed=False,
            rule_id="persuasion_speech",
            reason="wolf speech did not drive villager elimination",
        )

    if speaker_camp == Camp.VILLAGER.value:
        if elim_camp == Camp.WEREWOLF.value and speech.matched_round_elimination:
            return GenerationRuleResult(
                passed=True,
                rule_id="persuasion_speech",
                reason="villager drove werewolf elimination",
            )
        if (
            elim_camp == Camp.WEREWOLF.value
            and swing_to_final_vote >= 2
            and speech.elimination_drive_swings >= 1
        ):
            return GenerationRuleResult(
                passed=True,
                rule_id="persuasion_speech",
                reason="villager speech aligned final votes on wolf elimination",
            )
        return GenerationRuleResult(
            passed=False,
            rule_id="persuasion_speech",
            reason="villager speech did not help eliminate wolf or align votes",
        )

    return GenerationRuleResult(
        passed=False, rule_id="persuasion_speech", reason="unknown speaker camp"
    )


def evaluate_night_action_event(
    event: dict[str, Any], ctx: RunContext
) -> GenerationRuleResult | None:
    """夜间技能：有效目标 + 结果对己方有利。"""
    etype = str(event.get("event_type", ""))
    if etype not in NIGHT_ACTION_EVENT_TYPES:
        return None

    data = event.get("data") or {}
    actor_id = str(data.get("player_id") or data.get("voter_id") or "")
    target_id = str(data.get("target_id") or "")
    if not actor_id or actor_id not in ctx.roster:
        return None
    if not target_id:
        return GenerationRuleResult(
            passed=False,
            rule_id="night_action",
            reason=f"insufficient_material: {etype} without target_id",
        )

    target_camp = target_id_to_camp(target_id, ctx.roster)
    target_entry = ctx.roster.get(target_id)
    target_role = (target_entry.role_name or "") if target_entry else ""
    result = str(data.get("result") or "").lower()

    if etype == "seer_checked":
        if result in {"werewolf", "wolf"}:
            return GenerationRuleResult(
                passed=True, rule_id="night_action", reason="seer found werewolf"
            )
        return GenerationRuleResult(
            passed=False, rule_id="night_action", reason="seer check did not find werewolf"
        )

    if etype == "witch_poisoned":
        if target_camp == Camp.WEREWOLF.value:
            return GenerationRuleResult(
                passed=True, rule_id="night_action", reason="witch poisoned werewolf"
            )
        return GenerationRuleResult(
            passed=False, rule_id="night_action", reason="witch poison did not hit werewolf"
        )

    if etype == "witch_saved":
        if target_role in {"Seer", "Witch", "Guard", "Hunter"}:
            return GenerationRuleResult(
                passed=True, rule_id="night_action", reason="witch saved key role"
            )
        return GenerationRuleResult(
            passed=False, rule_id="night_action", reason="witch save target not key role"
        )

    if etype == "guard_protected":
        return GenerationRuleResult(
            passed=True, rule_id="night_action", reason="guard protection recorded"
        )

    return GenerationRuleResult(
        passed=False, rule_id="night_action", reason=f"night action not promoted: {etype}"
    )


def _speech_rank_score(speech: CampSpeechInfluence) -> int:
    score = speech.camp_aligned_score
    if speech.matched_round_elimination:
        score += 20
    score += speech.elimination_drive_swings * 5
    return score


def _night_rank_score(event: dict[str, Any]) -> int:
    etype = str(event.get("event_type", ""))
    data = event.get("data") or {}
    if etype == "witch_poisoned":
        base = 14
    elif etype == "seer_checked":
        base = 12
    elif etype == "witch_saved":
        base = 10
    else:
        base = 8
    result = str(data.get("result") or "").lower()
    if result in {"werewolf", "wolf"}:
        base += 6
    return base


def _swing_to_final_map(
    ctx: RunContext, camp_report: CampPersuasionReport
) -> dict[tuple[str, int], int]:
    from llm_werewolf.evaluation.scoring.intention import (
        _final_votes_by_round,
        _swing_to_final_vote_count,
    )

    final_votes = _final_votes_by_round(ctx.events)
    out: dict[tuple[str, int], int] = {}
    for speech in camp_report.speeches:
        key = (speech.speaker_id, speech.round_number)
        out[key] = _swing_to_final_vote_count(speech.round_number, speech.swings, final_votes)
    return out


def collect_skill_generation_candidates(
    ctx: RunContext, camp_report: CampPersuasionReport
) -> list[SkillGenerationCandidate]:
    candidates: list[SkillGenerationCandidate] = []
    seen_speech: set[tuple[str, int]] = set()
    swing_final = _swing_to_final_map(ctx, camp_report)

    for speech in camp_report.speeches:
        key = (speech.speaker_id, speech.round_number)
        if key in seen_speech:
            continue
        seen_speech.add(key)

        rule = evaluate_persuasion_speech(speech, ctx, swing_to_final_vote=swing_final.get(key, 0))
        if not rule.passed:
            continue

        entry = ctx.roster.get(speech.speaker_id)
        candidates.append(
            SkillGenerationCandidate(
                source_kind="persuasion_speech",
                prompt_role_key=_role_key_for_player(ctx, speech.speaker_id),
                player_id=speech.speaker_id,
                player_name=speech.speaker_name,
                game_role_name=entry.role_name if entry else None,
                camp=speech.speaker_camp or (entry.camp if entry else None),
                rule=rule,
                rank_score=_speech_rank_score(speech),
                speech=speech,
            )
        )

    seen_night: set[tuple[str, str, int]] = set()
    for event in ctx.events:
        rule = evaluate_night_action_event(event, ctx)
        if rule is None or not rule.passed:
            continue

        data = event.get("data") or {}
        actor_id = str(data.get("player_id") or data.get("voter_id") or "")
        etype = str(event.get("event_type", ""))
        rnd = int(event.get("round_number", 0))
        dedupe_key = (actor_id, etype, rnd)
        if dedupe_key in seen_night:
            continue
        seen_night.add(dedupe_key)

        entry = ctx.roster.get(actor_id)
        candidates.append(
            SkillGenerationCandidate(
                source_kind="night_action",
                prompt_role_key=_role_key_for_player(ctx, actor_id),
                player_id=actor_id,
                player_name=entry.player_name if entry else actor_id,
                game_role_name=entry.role_name if entry else None,
                camp=entry.camp if entry else None,
                rule=rule,
                rank_score=_night_rank_score(event),
                night_event=event,
            )
        )

    candidates.sort(key=lambda c: c.rank_score, reverse=True)
    return dedupe_skill_candidates(candidates)


def collect_skipped_candidates(
    ctx: RunContext, camp_report: CampPersuasionReport
) -> list[SkippedCandidate]:
    """记录未通过门控的素材，便于审核。"""
    skipped: list[SkippedCandidate] = []
    swing_final = _swing_to_final_map(ctx, camp_report)

    for speech in camp_report.speeches:
        rule = evaluate_persuasion_speech(
            speech,
            ctx,
            swing_to_final_vote=swing_final.get((speech.speaker_id, speech.round_number), 0),
        )
        if rule.passed:
            continue
        skipped.append(
            SkippedCandidate(
                source_kind="persuasion_speech",
                player_id=speech.speaker_id,
                player_name=speech.speaker_name,
                rule_id=rule.rule_id,
                reason=rule.reason,
            )
        )

    for event in ctx.events:
        rule = evaluate_night_action_event(event, ctx)
        if rule is None:
            continue
        if rule.passed:
            continue
        data = event.get("data") or {}
        actor_id = str(data.get("player_id") or data.get("voter_id") or "")
        entry = ctx.roster.get(actor_id)
        skipped.append(
            SkippedCandidate(
                source_kind="night_action",
                player_id=actor_id,
                player_name=entry.player_name if entry else actor_id,
                rule_id=rule.rule_id,
                reason=rule.reason,
            )
        )

    return skipped


def generation_rules_summary() -> dict[str, Any]:
    return {
        "phase": "camp_aware_gates",
        "score_filter": "disabled",
        "persuasion_speech": {
            "min_public_speech_len": MIN_PUBLIC_SPEECH_LEN,
            "wolf": "matched villager elimination",
            "villager": "matched werewolf elimination OR swing_to_final_vote>=2 with drive",
        },
        "night_action": {
            "event_types": sorted(NIGHT_ACTION_EVENT_TYPES),
            "requires": "outcome beneficial (e.g. seer finds wolf, witch poisons wolf)",
        },
        "no_placeholder": "identities without passing material are omitted from skills[]",
        "dedupe": "per role: max 1 persuasion + 1 night event type; max 2 skills per role per run",
        "belief_when_to_use": "when beliefs.jsonl exists, enrich when_to_use with B1/B2 distribution and vote intention",
    }
