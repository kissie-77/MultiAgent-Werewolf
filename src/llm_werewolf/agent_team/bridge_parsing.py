"""Pure parsing helpers for WerewolfAdapterBridge."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.seat import resolve_player_by_seat
from llm_werewolf.strategy.decisions import (
    SpeechDecision,
    extract_public_text,
    normalize_speech_decision,
)

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


def parse_target_selection(
    response: str, possible_targets: list[PlayerProtocol], allow_skip: bool = False
) -> PlayerProtocol | None:
    if allow_skip and re.search(r"\bskip\b", response, flags=re.I):
        return None

    numbers = re.findall(r"\d+", response.strip())
    if not numbers:
        return None

    try:
        seat = int(numbers[0])
        if allow_skip and seat == 0:
            return None
        return resolve_player_by_seat(seat, possible_targets)
    except (ValueError, IndexError):
        return None


def parse_yes_no(response: str) -> bool:
    from llm_werewolf.game_runtime.prompts.yes_no_parse import parse_yes_no_strict

    return parse_yes_no_strict(response)


def parse_multi_target_selection(
    response: str, possible_targets: list[PlayerProtocol], num_targets: int
) -> list[PlayerProtocol] | None:
    numbers = re.findall(r"\d+", response.strip())
    if len(numbers) != num_targets:
        return None

    try:
        selected: list[PlayerProtocol] = []
        for num_str in numbers:
            seat = int(num_str)
            target = resolve_player_by_seat(seat, possible_targets)
            if target is None:
                return None
            selected.append(target)

        if len(selected) != len({p.player_id for p in selected}):
            return None
        return selected
    except (ValueError, IndexError):
        return None


def parse_speech(response: str) -> SpeechDecision:
    """将模型原始文本拆分为公开发言与私人推理。"""
    private_blocks = re.findall(r"\{([^}]*)\}", response, flags=re.S)
    private_thought = "\n".join(b.strip() for b in private_blocks if b.strip()) or None
    decision = SpeechDecision.model_construct(
        public_speech=extract_public_text(response), private_thought=private_thought
    )
    return normalize_speech_decision(decision, raw_fallback=response)
