"""基于角色策略库 + 对局证据，生成高质量、可区分的 Skill 卡片文案。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from dataclasses import dataclass

if TYPE_CHECKING:
    from llm_werewolf.evaluation.post_game.run_context import RunContext
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampSpeechInfluence

# 策略要点提炼自 strategy/prompts/v2/roles/*.yaml 与常见网规狼人杀思路
_ROLE_DAY_PERSUASION: dict[str, dict[str, str]] = {
    "wolf": {
        "when": "白天讨论进入归票阶段，场上出现可抗推的「逻辑漏洞位」或需要统一狼队票型时",
        "behavior": (
            "① 用公开信息构建怀疑链（发言前后矛盾、投票与站边不一致、回避关键问题）；"
            "② 给出单一归票目标与一句可跟票理由，避免多目标分散；"
            "③ 适度踩高威胁好人，但避免与狼队友形成固定绑定。"
        ),
        "avoid": (
            "① 引用夜间私密信息或暗示「已知刀口/验人」；"
            "② 空泛划水、只防守不带票型；"
            "③ 为保队友强行改口导致自身逻辑崩盘。"
        ),
    },
    "wolf_king": {
        "when": "白天需要冲锋带节奏，或为后续被放逐时的开枪收益做铺垫时",
        "behavior": (
            "① 主动制造对立面，吸引火力到可控目标；"
            "② 归票时优先推走对狼队威胁最大的神职或强势平民；"
            "③ 若预判将被放逐，发言中预留「带走高价值目标」的叙事空间。"
        ),
        "avoid": "过早暴露狼王身份、无收益硬跳神职、开枪前把票型搅乱导致队友被误出",
    },
    "prophet": {
        "when": "白天需要报验、带队或回应悍跳，且已有可验证的查验信息时",
        "behavior": (
            "① 先报「第几晚验谁、结果是什么」，再解释验人动机；"
            "② 用验人结果串联投票链，推动集中票型；"
            "③ 信息不足时可逻辑试探，避免无验人裸跳。"
        ),
        "avoid": "报验无先后逻辑、连续改口、把未验玩家当定狼、暴露后不提供备用归票方案",
    },
    "witch": {
        "when": "白天需要解释用药逻辑、回应刀口质疑或引导毒口时",
        "behavior": (
            "① 仅在必要时透露用药信息，并与公开死亡/发言对齐；"
            "② 推动大家关注「谁更像狼」而非纠缠女巫身份；"
            "③ 毒药意向可暗示但不提前锁死无收益毒口。"
        ),
        "avoid": "过早亮双药、编造与事件不符的用药、情绪化毒口、把解药浪费在自刀嫌疑位",
    },
    "guard": {
        "when": "白天需要用守护逻辑辅助排坑，或回应「为何某人未死」的质疑时",
        "behavior": (
            "① 仅在能形成排坑收益时透露守护路径；"
            "② 用「不能连守同一人」规则解释守护取舍；"
            "③ 引导好人关注狼刀规律而非猜测守卫身份。"
        ),
        "avoid": "每轮暗示守护对象、与女巫解药叙事冲突、无收益裸跳守卫",
    },
    "hunter": {
        "when": "白天被怀疑或进入焦点位，需要表态站边又不暴露过多时",
        "behavior": (
            "① 给出清晰站边与投票理由，减少被抗推概率；"
            "② 强调「若出局会带走最可疑者」以形成威慑；"
            "③ 优先整理发言矛盾链，而非空喊身份。"
        ),
        "avoid": "过早拍身份、情绪化开枪预告、无逻辑跟票",
    },
    "villager": {
        "when": "白天需要整理信息、推动可验证的怀疑链时",
        "behavior": (
            "① 对比发言与投票的一致性，指出回避关键问题的人；"
            "② 不强行认定神职真假，但要求给出可验证理由；"
            "③ 归票时给出单一目标与跟票理由。"
        ),
        "avoid": "无依据神职认定、分票、复读他人观点不带新信息",
    },
}

_NIGHT_EVENT_STRATEGY: dict[str, dict[str, str]] = {
    "seer_checked": {
        "title": "预言家查验决策",
        "when_early": "首夜信息空窗，需在一验定方向的高收益目标中做选择",
        "when_late": "中后局需验证站边摇摆者、跟票异常者或对跳位",
        "behavior": (
            "① 优先验高置位、首日带节奏或投票摇摆的玩家；"
            "② 避免连续两晚验同一人；"
            "③ 记录 target 与 result，白天再择机报验。"
        ),
        "avoid": (
            "① 首夜盲验已建立可信好人面的玩家；"
            "② 为「验谁都是好」的低信息位浪费查验；"
            "③ 查到狼后不预留白天叙事直接暴露。"
        ),
    },
    "guard_protected": {
        "title": "守卫守护决策",
        "when_early": "首夜预判狼刀可能落在高价值神职或明好人",
        "when_late": "根据前几轮刀口规律，保护最可能被刀的存活核心",
        "behavior": (
            "① 优先守护疑似预言家/女巫/强势好人；"
            "② 遵守「不能连续两晚守同一人」；"
            "③ 兼顾与女巫解药不冲突的守护路径。"
        ),
        "avoid": "连守同一人、只守自己、无规律乱守导致神职裸奔",
    },
    "witch_saved": {
        "title": "女巫解药使用",
        "when_early": "首夜刀口落在关键神职或高价值好人",
        "when_late": "残局保能带队者或能形成票型优势的核心",
        "behavior": (
            "① 评估被刀者身份价值与自刀嫌疑；② 关键神职优先于普通平民；③ 用药后白天谨慎透露信息。"
        ),
        "avoid": "首夜盲救低价值位、忽视自刀骗药、用药后立即暴露女巫",
    },
    "witch_poisoned": {
        "title": "女巫毒药使用",
        "when_early": "仅在有高置信悍跳狼或定狼位时使用",
        "when_late": "残局毒掉能改票型的确认狼或分票者",
        "behavior": (
            "① 毒口优先：悍跳对跳位 > 发言投票双标 > 破坏阵型者；"
            "② 与白天归票方向尽量一致；"
            "③ 用完即进入「单药」叙事管理。"
        ),
        "avoid": "情绪毒、无证据毒强势好人、与解药逻辑自相矛盾",
    },
    "werewolf_killed": {
        "title": "狼队刀口决策",
        "when_early": "首夜优先削弱神职或高置位带节奏好人",
        "when_late": "刀掉能验/能带队的存活核心，或制造混乱",
        "behavior": (
            "① 狼队内部先对齐单一刀口再落刀；"
            "② 优先：预言家 > 女巫 > 守卫 > 强势平民；"
            "③ 考虑守卫/女巫解药可能的拦截。"
        ),
        "avoid": "刀口分散、刀明好人浪费轮次、为刀而刀不记白天叙事",
    },
}

_RESULT_ZH = {"werewolf": "狼人", "wolf": "狼人", "villager": "好人", "good": "好人"}


@dataclass(frozen=True)
class SkillCardContent:
    title_zh: str
    when_to_use: str
    public_behavior: str
    avoid: str


def _player_label(ctx: RunContext, player_id: str | None) -> str:
    if not player_id:
        return "未知目标"
    entry = ctx.roster.get(player_id)
    if entry and entry.player_name and entry.player_name != player_id:
        return f"{entry.player_name}（{player_id}）"
    return player_id


def _result_zh(raw: Any) -> str:
    if raw is None:
        return "未知"
    key = str(raw).strip().lower()
    return _RESULT_ZH.get(key, str(raw))


def _round_phase_hint(round_number: int) -> str:
    if round_number <= 1:
        return "early"
    if round_number <= 3:
        return "mid"
    return "late"


def _seer_target_motivation(
    ctx: RunContext, *, target_id: str, check_result: str, round_number: int
) -> str:
    entry = ctx.roster.get(target_id)
    role_name = entry.role_name if entry else None
    if check_result == "狼人":
        if role_name in {"AlphaWolf", "WolfKing"}:
            return "高置位或末置位常藏狼王/狼队核心，首验收益高"
        return "该位首日发言或票型有摇摆，需用查验定阵营"
    if round_number <= 1:
        return "首夜优先排除高信息位，为白天排坑留锚点"
    return "中局验人优先跟进站边异常者，验证投票链"


def _guard_target_motivation(ctx: RunContext, *, target_id: str, round_number: int) -> str:
    entry = ctx.roster.get(target_id)
    role_name = entry.role_name if entry else None
    if role_name == "Seer":
        return "预言家是狼队首刀高价值目标，首夜守验可保信息链"
    if role_name == "Witch":
        return "女巫双药未交前是核心，守女巫可防首刀断药"
    if round_number <= 1:
        return "首夜无信息时守高置位或首日发言积极者，博刀口命中"
    return "按前几轮刀口规律，保护仍存活且能带队的核心位"


def build_wolf_night_coordination_card(
    *, round_number: int, speeches: list[str], kill_target_id: str | None, ctx: RunContext
) -> SkillCardContent:
    kill_label = _player_label(ctx, kill_target_id) if kill_target_id else "待对齐刀口"
    excerpt = "；".join(s.strip() for s in speeches if s.strip())[:120]
    return SkillCardContent(
        title_zh=f"第{round_number}轮狼队夜间刀口协商",
        when_to_use=(
            f"第{round_number}轮狼队私密频道，需在落刀前统一目标；优先神职 > 能带队平民 > 划水位。"
        ),
        public_behavior=(
            "① 夜间先报「建议刀口 + 一句理由」，等队友表态后再收敛到单一目标；"
            "② 理由用「高置位/像神职/发言像预言家」等可白天自洽的说法，不用夜间私密细节；"
            f"③ 本局最终刀口对齐 {kill_label}。" + (f" 协商摘录：{excerpt}。" if excerpt else "")
        ),
        avoid=(
            "① 各狼各刀各的、白天叙事与刀口对不上；"
            "② 夜间直接报真实身份或引用验人/用药；"
            "③ 为刀而刀不记白天怎么解释。"
        ),
    )


def build_persuasion_skill_card(
    *, role_key: str, speech: CampSpeechInfluence, ctx: RunContext
) -> SkillCardContent:
    base = _ROLE_DAY_PERSUASION.get(role_key, _ROLE_DAY_PERSUASION["villager"])
    rnd = speech.round_number
    title = f"第{rnd}轮阵营正向说服"
    if speech.matched_round_elimination:
        title = f"第{rnd}轮说服并命中放逐"

    when = base["when"]
    if speech.matched_round_elimination:
        when += f"；本局发言后 {speech.camp_aligned_swings} 人改票且当轮放逐与归票一致"
    else:
        when += f"；本局发言后产生 {speech.camp_aligned_swings} 次同阵营意向摇摆"

    behavior = base["behavior"]
    excerpt = (speech.public_speech or "").strip()
    if excerpt and len(excerpt) >= 12:
        behavior += f" ④ 表述上可先点出具体矛盾，再收束到单一归票（如摘录：「{excerpt[:80]}…」）。"

    return SkillCardContent(
        title_zh=title, when_to_use=when, public_behavior=behavior, avoid=base["avoid"]
    )


def build_night_action_skill_card(
    *, role_key: str, event: dict[str, Any], ctx: RunContext
) -> SkillCardContent:
    etype = str(event.get("event_type", "night_action"))
    data = event.get("data") or {}
    rnd = int(event.get("round_number", 0))
    target_id = str(data.get("target_id") or "")
    target_label = _player_label(ctx, target_id or None)
    check_result = _result_zh(data.get("result"))

    strat = _NIGHT_EVENT_STRATEGY.get(etype)
    if strat is None:
        return SkillCardContent(
            title_zh=f"第{rnd}轮夜间决策",
            when_to_use=f"第{rnd}轮夜间，信息边界与当时一致时",
            public_behavior="在合法目标内做出与阵营收益一致的单一选择",
            avoid="无效目标、重复无收益操作、泄露不应公开的信息",
        )

    phase = _round_phase_hint(rnd)
    when = strat["when_early"] if phase == "early" else strat["when_late"]
    when = f"第{rnd}轮夜间：{when}。"

    behavior = strat["behavior"]
    if etype == "seer_checked" and target_id:
        motive = _seer_target_motivation(
            ctx, target_id=target_id, check_result=check_result, round_number=rnd
        )
        behavior += f" 本局验 {target_label}（{motive}），结果 {check_result}。"
    elif etype == "guard_protected" and target_id:
        motive = _guard_target_motivation(ctx, target_id=target_id, round_number=rnd)
        behavior += f" 本局守 {target_label}（{motive}）。"
    elif target_id:
        behavior += f" 本局选择目标 {target_label}。"

    return SkillCardContent(
        title_zh=f"第{rnd}轮{strat['title']}",
        when_to_use=when,
        public_behavior=behavior,
        avoid=strat["avoid"],
    )


def dedupe_skill_candidates(candidates: list[Any], *, max_per_role: int = 2) -> list[Any]:
    """同局内去重：每身份保留高分且场景不重复的 Skill。"""
    if not candidates:
        return []

    def dedupe_key(candidate: Any) -> tuple[str, ...]:
        role = candidate.prompt_role_key
        if candidate.source_kind == "persuasion_speech":
            return (role, "persuasion")
        etype = str((candidate.night_event or {}).get("event_type", ""))
        return (role, "night", etype)

    def sort_key(candidate: Any) -> tuple[int, int]:
        rnd = 0
        if candidate.night_event:
            rnd = int(candidate.night_event.get("round_number", 0))
        elif candidate.speech:
            rnd = candidate.speech.round_number
        return (candidate.rank_score, rnd)

    best_by_key: dict[tuple[str, ...], Any] = {}
    for candidate in candidates:
        key = dedupe_key(candidate)
        prev = best_by_key.get(key)
        if prev is None or sort_key(candidate) > sort_key(prev):
            best_by_key[key] = candidate

    deduped = sorted(best_by_key.values(), key=lambda c: c.rank_score, reverse=True)

    per_role: dict[str, int] = {}
    selected: list[Any] = []
    for candidate in deduped:
        role = candidate.prompt_role_key
        count = per_role.get(role, 0)
        if count >= max_per_role:
            continue
        per_role[role] = count + 1
        selected.append(candidate)

    return selected
