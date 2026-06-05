"""Prompt builders used by WerewolfAdapterBridge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.support.seat import get_player_seat
from llm_werewolf.strategy.contracts.decisions import (
    generate_response_instruction,
    mind_state_schema_instruction,
    seat_choice_schema_instruction,
    speech_schema_instruction,
    vote_intention_schema_instruction,
    witch_night_schema_instruction,
)
from llm_werewolf.strategy.contracts.phase_outputs import (
    ActionPhase,
    RoundtablePhase,
    action_phase_instruction,
    roundtable_phase_instruction,
)
from llm_werewolf.strategy.registry.role_prompts import ROLE_SEAT_ACTION, GamePrompts
from llm_werewolf.strategy.voting.intention import VoteIntentionAnchor

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


def build_target_selection_prompt(
    role_name: str,
    action_description: str,
    possible_targets: list[PlayerProtocol],
    allow_skip: bool = False,
    additional_context: str = "",
    round_number: int | None = None,
    phase: str | None = None,
    *,
    structured: bool = False,
    action_phase: ActionPhase | None = None,
    require_reason: bool = False,
) -> str:
    prompt_parts = [f"你是{role_name}。"]

    if round_number is not None and phase:
        prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")
    elif round_number is not None:
        prompt_parts.append(f"当前回合：{round_number}")

    prompt_parts.extend([f"任务：{action_description}", ""])

    if additional_context:
        prompt_parts.extend([additional_context, ""])

    prompt_parts.append("可选目标：")
    for target in possible_targets:
        seat = get_player_seat(target)
        seat_label = seat if seat is not None else target.player_id
        prompt_parts.append(f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）")

    if allow_skip:
        prompt_parts.append("- 座位 0：跳过（不执行此行动）")

    suppress_role_action_line = action_phase in {
        ActionPhase.DAY_VOTE,
        ActionPhase.SHERIFF_VOTE,
        ActionPhase.BADGE_TRANSFER,
    }
    if not suppress_role_action_line:
        action_line = ROLE_SEAT_ACTION.get(role_name, GamePrompts.PROPHET_ACTION)
        prompt_parts.extend(["", action_line])
    if action_phase is not None:
        prompt_parts.extend(["", action_phase_instruction(action_phase)])
    if structured:
        prompt_parts.extend([
            "",
            seat_choice_schema_instruction(
                allow_skip=allow_skip,
                require_reason=require_reason or action_phase == ActionPhase.DAY_VOTE,
            ),
        ])
    else:
        prompt_parts.extend([
            "",
            "请只回复目标玩家的全局座位号，放在 [[数字]] 中。",
            "使用真实座位号，不是列表序号。不要输出其他文字。",
        ])
    return "\n".join(prompt_parts)


def build_yes_no_prompt(
    role_name: str,
    question: str,
    context: str = "",
    round_number: int | None = None,
    phase: str | None = None,
    *,
    structured: bool = False,
) -> str:
    prompt_parts = [f"你是{role_name}。"]

    if round_number is not None and phase:
        prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")
    elif round_number is not None:
        prompt_parts.append(f"当前回合：{round_number}")

    prompt_parts.append(f"问题：{question}")

    if context:
        prompt_parts.extend(["", context])

    if structured:
        prompt_parts.extend([
            "",
            "请调用 generate_response：choice=true 表示是，false 表示否。",
            generate_response_instruction("YesNoDecision"),
        ])
    else:
        prompt_parts.extend(["", "请只回复 [[1]] 表示是，[[0]] 表示否。不要输出其他文字。"])
    return "\n".join(prompt_parts)


def build_multi_target_prompt(
    role_name: str,
    action_description: str,
    possible_targets: list[PlayerProtocol],
    num_targets: int,
    additional_context: str = "",
    round_number: int | None = None,
    phase: str | None = None,
    *,
    structured: bool = False,
) -> str:
    prompt_parts = [f"你是{role_name}。"]

    if round_number is not None and phase:
        prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")
    elif round_number is not None:
        prompt_parts.append(f"当前回合：{round_number}")

    prompt_parts.extend([
        f"任务：{action_description}",
        f"请选择 {num_targets} 个不同目标。",
        "",
    ])

    if additional_context:
        prompt_parts.extend([additional_context, ""])

    prompt_parts.append("可选目标：")
    for target in possible_targets:
        seat = get_player_seat(target)
        seat_label = seat if seat is not None else target.player_id
        prompt_parts.append(f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）")

    if structured:
        prompt_parts.extend([
            "",
            f"请调用 generate_response，在 seats 字段填写 {num_targets} 个互不重复的全局座位号。",
            generate_response_instruction("MultiSeatChoiceDecision"),
        ])
    else:
        prompt_parts.extend([
            "",
            f"请回复 {num_targets} 个全局座位号，用逗号分隔，例如：1, 3",
            "使用真实座位号，不是列表序号。",
        ])
    return "\n".join(prompt_parts)


def build_speech_prompt(
    context: str,
    instruction: str = "",
    *,
    structured: bool = True,
    roundtable_phase: RoundtablePhase | None = None,
) -> str:
    parts = [context]
    if instruction:
        parts.extend(["", instruction])
    parts.extend(["", GamePrompts.SPEECH_PROMPT])
    if roundtable_phase is not None:
        parts.extend(["", roundtable_phase_instruction(roundtable_phase)])
    elif structured:
        parts.extend(["", speech_schema_instruction()])
    else:
        parts.extend([
            "",
            speech_schema_instruction(),
            "（兼容模式）若无法调用工具，可用 [[完整中文发言]] 与 {...} 私人推理，",
            "引擎将尽量解析为 SpeechDecision。",
        ])
    return "\n".join(parts)


def build_witch_night_prompt(
    role_name: str,
    *,
    can_see_victim: bool,
    can_save: bool,
    victim_line: str,
    poison_targets: list[PlayerProtocol],
    additional_context: str = "",
    round_number: int | None = None,
    phase: str | None = None,
    structured: bool = False,
) -> str:
    prompt_parts = [f"你是{role_name}。", GamePrompts.WITCH_OPEN, ""]

    if round_number is not None and phase:
        prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")

    if can_see_victim and victim_line:
        prompt_parts.extend(["", victim_line])
    elif not can_save:
        prompt_parts.extend(["", "本夜没有可救刀口信息，不能选择 save。"])

    if additional_context:
        prompt_parts.extend(["", additional_context, ""])

    if poison_targets:
        prompt_parts.append("若选择 poison，可选毒杀目标：")
        for target in poison_targets:
            seat = get_player_seat(target)
            seat_label = seat if seat is not None else target.player_id
            prompt_parts.append(f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）")

    prompt_parts.append("")
    if can_save and poison_targets:
        prompt_parts.extend([
            "请在本回合三选一：救人(save) / 毒人(poison) / 不行动(none)。",
            "救人会使用解药救今晚刀口；毒人需指定 seat。",
        ])
    elif can_save:
        prompt_parts.extend([
            "请在本回合二选一：救人(save) / 不行动(none)。",
            "救人会使用解药救今晚刀口。",
        ])
    elif poison_targets:
        prompt_parts.extend([
            "请在本回合二选一：毒人(poison) / 不行动(none)。",
            "解药不可用或没有可救刀口，不能选择 save；毒人需指定 seat。",
        ])
    else:
        prompt_parts.append("本回合没有可执行药水行动，请选择不行动(none)。")
    prompt_parts.extend(["", action_phase_instruction(ActionPhase.WITCH_NIGHT)])
    if structured:
        prompt_parts.extend([
            "",
            witch_night_schema_instruction(can_save=can_save),
        ])
    return "\n".join(prompt_parts)


def build_vote_intention_prompt(
    role_name: str,
    possible_targets: list[PlayerProtocol],
    additional_context: str,
    *,
    anchor: VoteIntentionAnchor,
    last_speaker_name: str | None = None,
    round_number: int | None = None,
    phase: str | None = None,
    structured: bool = False,
) -> str:
    if anchor == VoteIntentionAnchor.INITIAL:
        situation = "本轮讨论刚刚开始，尚无人发言。请上报你此刻若进行放逐投票会投给谁。"
    else:
        situation = (
            f"你刚听完 {last_speaker_name or '上一位玩家'} 的发言（已写入对话记忆）。"
            "请根据最新讨论更新：若此刻投票会放逐谁？"
        )
    prompt_parts = [
        f"你是{role_name}。",
        "",
        "【投票意向采集 · 非正式投票】",
        situation,
        "你必须明确给出意向：有目标填 seat=全局座位号；观望/无明确目标填 seat=0。",
        "seat=0 也必须由你主动选择，不可省略回复。",
    ]
    if round_number is not None and phase:
        prompt_parts.append(f"当前：第 {round_number} 轮 — {phase}")

    if additional_context:
        prompt_parts.extend(["", additional_context, ""])

    if possible_targets:
        prompt_parts.append("可选放逐目标（全局座位号）：")
        for target in possible_targets:
            seat = get_player_seat(target)
            seat_label = seat if seat is not None else "?"
            prompt_parts.append(f"- 座位 {seat_label}：{target.name}（ID: {target.player_id}）")

    prompt_parts.extend(["", action_phase_instruction(ActionPhase.VOTE_INTENTION)])
    if structured:
        prompt_parts.extend(["", vote_intention_schema_instruction()])
    return "\n".join(prompt_parts)


def build_mind_state_prompt(
    role_name: str,
    possible_targets: list[PlayerProtocol],
    additional_context: str,
    *,
    anchor: VoteIntentionAnchor,
    last_speaker_name: str | None = None,
    round_number: int | None = None,
    phase: str | None = None,
    structured: bool = False,
    belief_summary: str = "",
    wolf_camp_context: str = "",
) -> str:
    base = build_vote_intention_prompt(
        role_name,
        possible_targets,
        additional_context,
        anchor=anchor,
        last_speaker_name=last_speaker_name,
        round_number=round_number,
        phase=phase,
        structured=False,
    )
    prompt_parts = [
        base.replace("【投票意向采集 · 非正式投票】", "【心智状态采集 · 投票意向 + 信念矩阵 · 非正式投票】"),
    ]
    if belief_summary:
        prompt_parts.extend(["", belief_summary])
    if wolf_camp_context:
        prompt_parts.extend(["", wolf_camp_context])
    if structured:
        prompt_parts.extend(["", mind_state_schema_instruction()])
    return "\n".join(prompt_parts)
