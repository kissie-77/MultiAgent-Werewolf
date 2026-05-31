"""Offline DemoAgent policy aligned with WerewolfAdapterBridge prompts."""

from __future__ import annotations

import re
from enum import Enum
from random import Random

from llm_werewolf.strategy.decisions import (
    BeliefEntry,
    ExposureRadarDelta,
    GodRoleDelta,
    MindStateDecision,
    SecondOrderEntry,
    WolfCampDelta,
    is_valid_public_speech,
)

_SEAT_LINE = re.compile(r"^\s*-\s*座位\s*(\d+)")


class DemoPromptKind(str, Enum):
    YES_NO = "yes_no"
    VOTE_INTENTION = "vote_intention"
    MIND_STATE = "mind_state"
    WITCH = "witch"
    MULTI_SEAT = "multi_seat"
    SEAT_CHOICE = "seat_choice"
    SPEECH = "speech"


DEFAULT_SPEECH = (
    "目前场上信息还不够，我需要多听几轮发言再做判断。"
    "先观察大家的站队和投票倾向，重点关注发言前后矛盾的人。"
)


def classify_prompt(message: str) -> DemoPromptKind:
    """Map bridge-built prompts to a response strategy."""
    if "三选一" in message or "救人(save)" in message or "WitchNightDecision" in message:
        return DemoPromptKind.WITCH
    if "MindStateDecision" in message or "心智状态采集" in message:
        return DemoPromptKind.MIND_STATE
    if "投票意向采集" in message or "VoteIntentionDecision" in message:
        return DemoPromptKind.VOTE_INTENTION
    if "MultiSeatChoiceDecision" in message or re.search(r"选择\s*(\d+)\s*个不同目标", message):
        return DemoPromptKind.MULTI_SEAT
    if "[[1]] 表示是" in message or ("表示是" in message and "表示否" in message):
        return DemoPromptKind.YES_NO
    if (
        "请只回复目标玩家的全局座位号" in message
        or "SeatChoiceDecision" in message
        or "可选放逐目标" in message
        or "可选目标" in message
    ):
        return DemoPromptKind.SEAT_CHOICE
    return DemoPromptKind.SPEECH


def extract_seats(message: str) -> list[int]:
    seats: list[int] = []
    for line in message.splitlines():
        match = _SEAT_LINE.match(line)
        if match:
            seats.append(int(match.group(1)))
    return seats


def extract_multi_count(message: str) -> int:
    match = re.search(r"选择\s*(\d+)\s*个不同目标", message) or re.search(
        r"回复\s*(\d+)\s*个全局座位号", message
    )
    return int(match.group(1)) if match else 1


def build_speech(seat_number: int, role_display: str) -> str:
    text = (
        f"我是{role_display}，{seat_number} 号位。"
        "我会先完整听完本轮发言，再结合投票意向判断最可疑的对象。"
    )
    return text if is_valid_public_speech(text) else DEFAULT_SPEECH


def pick_seat(seats: list[int], seat_number: int, *, allow_skip: bool, rng: Random, random_mode: bool) -> int:
    candidates = [seat for seat in seats if seat > 0]
    if not candidates:
        return 0
    if allow_skip and not random_mode and seat_number % 5 == 0:
        return 0
    if random_mode:
        return rng.choice(candidates)  # noqa: S311
    return candidates[(seat_number - 1) % len(candidates)]


def _extract_last_speaker_seat(message: str) -> int | None:
    match = re.search(r"刚听完\s*(\S+)\s*的发言", message)
    if not match:
        return None
    for line in message.splitlines():
        if match.group(1) in line and (seat_match := _SEAT_LINE.match(line)):
            return int(seat_match.group(1))
    return None


def _extract_previous_vote_seat(message: str) -> int | None:
    match = re.search(r"上一帧投票意向:\s*(\d+)\s*号", message)
    if match:
        return int(match.group(1))
    if "上一帧投票意向: 观望" in message:
        return 0
    return None


def build_mind_state(
    message: str,
    *,
    seat_number: int,
    rng: Random,
    random_mode: bool,
    is_wolf: bool = False,
) -> MindStateDecision:
    seats = extract_seats(message)
    vote_seat = pick_seat(seats, seat_number, allow_skip=True, rng=rng, random_mode=random_mode)
    actor_seat = seat_number or 1
    previous_vote_seat = _extract_previous_vote_seat(message)

    first_order: list[BeliefEntry] = []
    if vote_seat > 0:
        first_order.append(
            BeliefEntry(
                target_seat=vote_seat,
                wolf_probability=round(min(0.95, 0.45 + (vote_seat % 4) * 0.1), 2),
                reason="demo: 当前投票意向对应座位可疑度上调",
            )
        )

    second_order: list[SecondOrderEntry] = []
    speaker_seat = _extract_last_speaker_seat(message)
    if speaker_seat and speaker_seat != actor_seat:
        second_order.append(
            SecondOrderEntry(
                observer_seat=speaker_seat,
                suspects_me_as_wolf=round(0.12 + (actor_seat % 3) * 0.08, 2),
                reason="demo: 刚听完发言后对暴露风险的估计",
            )
        )

    vote_reason = "demo mind state"
    if previous_vote_seat is not None and vote_seat != previous_vote_seat:
        vote_reason = f"demo: 意向从 {previous_vote_seat} 调整为 {vote_seat}"

    wolf_camp_delta: WolfCampDelta | None = None
    if is_wolf and seats:
        intel_target = next((s for s in seats if s != actor_seat), seats[0])
        wolf_camp_delta = WolfCampDelta(
            god_role_intel=[
                GodRoleDelta(
                    target_seat=intel_target,
                    delta={"Seer": 0.35, "Villager": 0.65},
                    reason="demo wolf intel",
                )
            ],
            exposure_radar=[
                ExposureRadarDelta(
                    wolf_seat=actor_seat,
                    observer_seat=intel_target,
                    suspicion=0.18 + (actor_seat % 2) * 0.1,
                    reason="demo wolf exposure",
                )
            ],
        )

    return MindStateDecision(
        seat=vote_seat,
        reason=vote_reason,
        first_order=first_order,
        second_order=second_order,
        wolf_camp_delta=wolf_camp_delta,
    )


def respond(
    message: str,
    *,
    seat_number: int,
    rng: Random,
    role_display: str = "玩家",
    random_mode: bool = False,
) -> str:
    """Produce a bridge-parseable response for offline / smoke runs."""
    kind = classify_prompt(message)
    seats = extract_seats(message)
    allow_skip = "座位 0" in message or "跳过" in message or "观望" in message
    actor_seat = seat_number or 1

    if kind == DemoPromptKind.YES_NO:
        if random_mode:
            return rng.choice(["[[1]]", "[[0]]"])  # noqa: S311
        return "[[1]]" if actor_seat % 2 == 1 else "[[0]]"

    if kind == DemoPromptKind.VOTE_INTENTION:
        seat = pick_seat(seats, actor_seat, allow_skip=True, rng=rng, random_mode=random_mode)
        return f"[[{seat}]]"

    if kind == DemoPromptKind.MIND_STATE:
        seat = pick_seat(seats, actor_seat, allow_skip=True, rng=rng, random_mode=random_mode)
        return f"[[{seat}]]"

    if kind == DemoPromptKind.WITCH:
        if "刀口" in message or "被狼人击杀" in message or "击杀" in message:
            if random_mode:
                return rng.choice(["save", "none", "none"])  # noqa: S311
            return "save" if actor_seat % 2 == 1 else "none"
        poison_seats = [seat for seat in seats if seat > 0]
        if poison_seats and actor_seat % 4 == 0:
            target = pick_seat(
                poison_seats, actor_seat, allow_skip=False, rng=rng, random_mode=random_mode
            )
            return f"poison [[{target}]]"
        return "none"

    if kind == DemoPromptKind.MULTI_SEAT:
        count = extract_multi_count(message)
        candidates = [seat for seat in seats if seat > 0]
        if random_mode:
            rng.shuffle(candidates)
        picks = candidates[:count]
        if len(picks) < count and candidates:
            picks = candidates[: min(count, len(candidates))]
        return ", ".join(str(seat) for seat in picks)

    if kind == DemoPromptKind.SEAT_CHOICE:
        seat = pick_seat(seats, actor_seat, allow_skip=allow_skip, rng=rng, random_mode=random_mode)
        return f"[[{seat}]]"

    speech = build_speech(actor_seat, role_display)
    if random_mode:
        variants = [
            speech,
            DEFAULT_SPEECH,
            f"{role_display}认为目前需要更多信息，暂不下结论，建议先听完整轮发言。",
        ]
        speech = rng.choice(variants)  # noqa: S311
    return f"[[{speech}]]{{先隐藏真实立场，继续观察。}}"


def fallback_speech(*, seat_number: int = 1, role_display: str = "玩家") -> str:
    """Bridge speech fallback hook."""
    return f"[[{build_speech(seat_number, role_display)}]]"
