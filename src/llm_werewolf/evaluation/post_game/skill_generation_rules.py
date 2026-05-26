"""Skill 生成规则（Phase 1）：判定「是否值得生成 Skill」，不做 benefit 分数筛选。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport, CampSpeechInfluence
from llm_werewolf.evaluation.post_game.mvp_sources import GoldenQuote, iter_golden_quotes, iter_wolf_night_plans
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.game_runtime.prompts.manager import PromptManager

MIN_PUBLIC_SPEECH_LEN = 8

# 有效夜间决策事件（data 含 actor player_id + target_id）
NIGHT_ACTION_EVENT_TYPES = frozenset({
    "seer_checked",
    "witch_saved",
    "witch_poisoned",
    "guard_protected",
    "werewolf_killed",
})

SkillSourceKind = Literal[
    "persuasion_speech",
    "night_action",
    "mvp_golden_quote",
    "wolf_night_plan",
]


@dataclass(frozen=True)
class GenerationRuleResult:
    """单条素材的规则判定结果。"""

    passed: bool
    rule_id: str
    reason: str


@dataclass
class SkillGenerationCandidate:
    """通过生成规则、待写入 role_skills / MD 的候选。"""

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
    mvp_quote: GoldenQuote | None = None


def _role_key_for_player(ctx: RunContext, player_id: str) -> str:
    entry = ctx.roster.get(player_id)
    if entry and entry.role_name:
        return PromptManager.get_prompt_role_key(entry.role_name)
    return "villager"


def evaluate_persuasion_speech(speech: CampSpeechInfluence) -> GenerationRuleResult:
    """白天公开发言：有实质内容 + 产生阵营匹配说服效果（或命中当轮放逐）。"""
    text = (speech.public_speech or "").strip()
    if len(text) < MIN_PUBLIC_SPEECH_LEN:
        return GenerationRuleResult(
            passed=False,
            rule_id="persuasion_speech",
            reason="insufficient_material: public_speech too short or empty",
        )

    has_influence = speech.camp_aligned_swings >= 1 and speech.camp_aligned_score > 0
    if speech.matched_round_elimination and speech.camp_aligned_swings >= 1:
        return GenerationRuleResult(
            passed=True,
            rule_id="persuasion_speech",
            reason="matched_round_elimination with camp_aligned_swings",
        )

    if has_influence:
        return GenerationRuleResult(
            passed=True,
            rule_id="persuasion_speech",
            reason="camp_aligned_swings >= 1 with non-empty public_speech",
        )

    return GenerationRuleResult(
        passed=False,
        rule_id="persuasion_speech",
        reason="insufficient_influence: no camp-aligned vote swing after speech",
    )


def evaluate_night_action_event(
    event: dict[str, Any],
    ctx: RunContext,
) -> GenerationRuleResult | None:
    """夜间技能事件：actor 在 roster 中且存在有效 target。"""
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

    return GenerationRuleResult(
        passed=True,
        rule_id="night_action",
        reason=f"valid night decision event: {etype}",
    )


def evaluate_mvp_golden_quote(quote: GoldenQuote) -> GenerationRuleResult:
    """MVP 金句：有实质摘录且维度得分>0，或为本场 MVP 玩家条目。"""
    text = (quote.excerpt or "").strip()
    if len(text) < MIN_PUBLIC_SPEECH_LEN:
        return GenerationRuleResult(
            passed=False,
            rule_id="mvp_golden_quote",
            reason="insufficient_material: excerpt too short",
        )
    if quote.score > 0 or quote.is_overall_mvp:
        return GenerationRuleResult(
            passed=True,
            rule_id="mvp_golden_quote",
            reason="mvp golden quote with positive dimension score or overall mvp",
        )
    return GenerationRuleResult(
        passed=False,
        rule_id="mvp_golden_quote",
        reason="insufficient_mvp_score",
    )


def evaluate_wolf_night_plan(quote: GoldenQuote) -> GenerationRuleResult:
    text = (quote.excerpt or "").strip()
    if len(text) < MIN_PUBLIC_SPEECH_LEN:
        return GenerationRuleResult(
            passed=False,
            rule_id="wolf_night_plan",
            reason="insufficient_material: wolf night speech too short",
        )
    if quote.score >= 12.0:
        return GenerationRuleResult(
            passed=True,
            rule_id="wolf_night_plan",
            reason="wolf_night speech_total meets mvp threshold",
        )
    return GenerationRuleResult(
        passed=False,
        rule_id="wolf_night_plan",
        reason="insufficient_wolf_night_score",
    )


def _mvp_quote_rank_score(quote: GoldenQuote) -> int:
    base = int(quote.score * 2)
    if quote.is_overall_mvp:
        base += 30
    if quote.extra.get("matched_elimination"):
        base += 15
    if quote.extra.get("kill_match_bonus"):
        base += 15
    return base


def _speech_rank_score(speech: CampSpeechInfluence) -> int:
    score = speech.camp_aligned_score
    if speech.matched_round_elimination:
        score += 20
    return score


def _night_rank_score(event: dict[str, Any]) -> int:
    etype = str(event.get("event_type", ""))
    if etype == "werewolf_killed":
        return 15
    if etype in {"witch_saved", "witch_poisoned"}:
        return 12
    if etype == "seer_checked":
        return 10
    return 8


def collect_skill_generation_candidates(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    mvp_payload: dict[str, Any] | None = None,
) -> list[SkillGenerationCandidate]:
    """按生成规则收集候选；未通过规则的 identity 不会出现在列表中。"""
    candidates: list[SkillGenerationCandidate] = []
    seen_speech: set[tuple[str, int]] = set()
    seen_mvp_keys: set[tuple[str, int, str]] = set()

    for speech in camp_report.speeches:
        key = (speech.speaker_id, speech.round_number)
        if key in seen_speech:
            continue
        seen_speech.add(key)

        rule = evaluate_persuasion_speech(speech)
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

    for quote in iter_golden_quotes(mvp_payload, ctx):
        dedupe = (quote.player_id, quote.round_number, quote.kind)
        if dedupe in seen_mvp_keys:
            continue
        rule = evaluate_mvp_golden_quote(quote)
        if not rule.passed:
            continue
        seen_mvp_keys.add(dedupe)
        if (quote.player_id, quote.round_number) in seen_speech and quote.kind == "public_persuasion":
            for c in candidates:
                if (
                    c.source_kind == "persuasion_speech"
                    and c.player_id == quote.player_id
                    and c.speech
                    and c.speech.round_number == quote.round_number
                ):
                    c.mvp_quote = quote
                    c.rank_score = max(c.rank_score, _mvp_quote_rank_score(quote))
                    break
            continue
        candidates.append(
            SkillGenerationCandidate(
                source_kind="mvp_golden_quote",
                prompt_role_key=quote.prompt_role_key,
                player_id=quote.player_id,
                player_name=quote.player_name,
                game_role_name=quote.role_name,
                camp=quote.camp,
                rule=rule,
                rank_score=_mvp_quote_rank_score(quote),
                mvp_quote=quote,
            )
        )

    for quote in iter_wolf_night_plans(mvp_payload, ctx):
        dedupe = (quote.player_id, quote.round_number, "wolf_night_plan")
        if dedupe in seen_mvp_keys:
            continue
        rule = evaluate_wolf_night_plan(quote)
        if not rule.passed:
            continue
        seen_mvp_keys.add(dedupe)
        candidates.append(
            SkillGenerationCandidate(
                source_kind="wolf_night_plan",
                prompt_role_key=quote.prompt_role_key,
                player_id=quote.player_id,
                player_name=quote.player_name,
                game_role_name=quote.role_name,
                camp=quote.camp,
                rule=rule,
                rank_score=_mvp_quote_rank_score(quote),
                mvp_quote=quote,
            )
        )

    candidates.sort(key=lambda c: c.rank_score, reverse=True)
    return candidates


def generation_rules_summary() -> dict[str, Any]:
    """写入 role_skills.json 的规则说明（便于队友对照）。"""
    return {
        "phase": "generation_only",
        "score_filter": "disabled",
        "persuasion_speech": {
            "min_public_speech_len": MIN_PUBLIC_SPEECH_LEN,
            "requires": "camp_aligned_swings >= 1 OR (matched_round_elimination AND swings >= 1)",
        },
        "night_action": {
            "event_types": sorted(NIGHT_ACTION_EVENT_TYPES),
            "requires": "actor in roster AND non-empty target_id",
        },
        "mvp_golden_quote": {
            "requires": "excerpt length >= min AND (score > 0 OR overall mvp player)",
        },
        "wolf_night_plan": {
            "requires": "speech_total >= 12 from mvp wolf_night_analysis",
        },
        "no_placeholder": "identities without passing material are omitted from skills[]",
    }
