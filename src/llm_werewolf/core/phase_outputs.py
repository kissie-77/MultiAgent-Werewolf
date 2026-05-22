"""Per sub-phase output contracts (Schema + prompt text)."""

from __future__ import annotations

from enum import Enum

from llm_werewolf.core.decisions import speech_schema_instruction

# Embedded in prompts so AgentScope legacy path never treats discussion as seat-only.
ROUNDTABLE_SPEECH_ONLY_MARKER = "【子阶段·仅发言】"


class RoundtablePhase(str, Enum):
    """Discussion roundtable sub-phases — all use SpeechDecision only."""

    DAY_DISCUSSION = "day_discussion"
    WOLF_TEAM_DISCUSSION = "wolf_team_discussion"
    SHERIFF_CAMPAIGN = "sheriff_campaign"


class ActionPhase(str, Enum):
    """Non-speech phases that use other Schemas (not SpeechDecision)."""

    NIGHT_KILL_VOTE = "night_kill_vote"
    NIGHT_SKILL_TARGET = "night_skill_target"
    DAY_VOTE = "day_vote"
    WITCH_YES_NO = "witch_yes_no"
    WITCH_NIGHT = "witch_night"
    SHERIFF_RUN = "sheriff_run"
    SHERIFF_VOTE = "sheriff_vote"
    DEATH_SHOOT = "death_shoot"
    BADGE_TRANSFER = "badge_transfer"


_PHASE_TASK: dict[RoundtablePhase, str] = {
    RoundtablePhase.DAY_DISCUSSION: (
        "【任务】白天公开讨论轮。分析局势、回应前置发言、表明站队。"
        "不得在本轮提交刀人/投票/验人/守人/用药目标。"
    ),
    RoundtablePhase.WOLF_TEAM_DISCUSSION: (
        "【任务】狼队夜间秘密讨论。与队友对齐今晚刀口思路，说明理由。"
        "不得输出 [[座位号]]、不得只回复数字、不得调用选刀 Schema（无 seat 字段）。"
        "选刀目标在讨论结束后的单独步骤提交。"
    ),
    RoundtablePhase.SHERIFF_CAMPAIGN: (
        "【任务】警长竞选发言。说明竞选理由与带队思路。"
        "不得输出投票对象或 [[座位号]]。"
    ),
}

_PHASE_FORBIDDEN: dict[RoundtablePhase, str] = {
    RoundtablePhase.DAY_DISCUSSION: (
        "【本阶段禁止】[[数字]]、[[7]]、仅座位号、刀人/投票/验人/守人/毒人指令、"
        "generate_response 的 seat / choice / seats 字段。"
    ),
    RoundtablePhase.WOLF_TEAM_DISCUSSION: (
        "【本阶段禁止】[[数字]]、仅「刀X」、seat 字段、choice 字段。"
        "讨论阶段只填 public_speech 与 private_thought。"
    ),
    RoundtablePhase.SHERIFF_CAMPAIGN: (
        "【本阶段禁止】[[数字]]、投票座位号、seat / choice 字段。"
    ),
}


_ACTION_SCHEMA_HINT: dict[ActionPhase, str] = {
    ActionPhase.NIGHT_KILL_VOTE: (
        "【本阶段输出】仅 SeatChoiceDecision：seat=全局座位号（弃票 0）。"
        "禁止 SpeechDecision、禁止长段发言。"
    ),
    ActionPhase.NIGHT_SKILL_TARGET: (
        "【本阶段输出】仅 SeatChoiceDecision：seat=技能目标座位号（允许 0 则跳过）。"
        "禁止 SpeechDecision。"
    ),
    ActionPhase.DAY_VOTE: (
        "【本阶段输出】仅 SeatChoiceDecision：seat=整数全局座位号（要放逐的玩家）；"
        "弃票 seat=0。结合上文讨论记录投票，禁止 SpeechDecision。"
    ),
    ActionPhase.WITCH_YES_NO: (
        "【本阶段输出】仅 YesNoDecision：choice=true/false。"
    ),
    ActionPhase.WITCH_NIGHT: (
        "【本阶段输出】仅 WitchNightDecision：action=save|poison|none；"
        "poison 时 seat=毒药目标座位号。"
    ),
    ActionPhase.SHERIFF_RUN: (
        "【本阶段输出】仅 SeatChoiceDecision：seat=[[1]] 参加竞选，[[0]] 不参加。"
    ),
    ActionPhase.SHERIFF_VOTE: (
        "【本阶段输出】仅 SeatChoiceDecision：seat=候选人座位号。"
    ),
    ActionPhase.DEATH_SHOOT: (
        "【本阶段输出】仅 SeatChoiceDecision：seat=开枪目标座位号。"
    ),
    ActionPhase.BADGE_TRANSFER: (
        "【本阶段输出】仅 SeatChoiceDecision：seat=继承警徽座位号，撕毁 [[0]]。"
    ),
}


def resolve_roundtable_phase(*, channel: str, phase: str) -> RoundtablePhase:
    if channel == "wolf_team":
        return RoundtablePhase.WOLF_TEAM_DISCUSSION
    if "sheriff" in phase.lower():
        return RoundtablePhase.SHERIFF_CAMPAIGN
    return RoundtablePhase.DAY_DISCUSSION


def roundtable_phase_instruction(rt_phase: RoundtablePhase) -> str:
    """Full output contract for a discussion roundtable turn."""
    return "\n".join([
        ROUNDTABLE_SPEECH_ONLY_MARKER,
        _PHASE_TASK[rt_phase],
        _PHASE_FORBIDDEN[rt_phase],
        "",
        speech_schema_instruction(),
    ])


def action_phase_instruction(action_phase: ActionPhase) -> str:
    return _ACTION_SCHEMA_HINT[action_phase]
