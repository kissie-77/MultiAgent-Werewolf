"""Offline DemoAgent policy aligned with WerewolfAdapterBridge prompts."""

from __future__ import annotations

import re
from enum import Enum
from random import Random

from llm_werewolf.strategy.decisions import is_valid_public_speech

_SEAT_LINE = re.compile(r"^\s*-\s*座位\s*(\d+)")


class DemoPromptKind(str, Enum):
    YES_NO = "yes_no"
    VOTE_INTENTION = "vote_intention"
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
