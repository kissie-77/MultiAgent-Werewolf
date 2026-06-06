"""Pure parsing helpers for WerewolfAdapterBridge."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.support.seat import resolve_player_by_seat
from llm_werewolf.strategy.contracts.decisions import (
    _SCHEMA_LABEL_PROBE,
    SpeechDecision,
    extract_public_text,
    split_labeled_speech,
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
    # 遗留约定：{...} 块为私域推理。但 JSON 倾倒 {"public_speech":...} 含 Schema 标签，
    # 不能当作私域，否则会把公开发言一起吞进 private。
    brace_private = "\n".join(
        b.strip()
        for b in re.findall(r"\{([^}]*)\}", response, flags=re.S)
        if b.strip() and not _SCHEMA_LABEL_PROBE.search(b)
    )
    # 模型把 private_thought 作为纯文本/JSON 标签写进正文时，也回收为私域推理。
    label_private = None
    if _SCHEMA_LABEL_PROBE.search(response):
        _, label_private = split_labeled_speech(response)
    private_thought = "\n".join(p for p in (brace_private, label_private) if p) or None
    decision = SpeechDecision.model_construct(
        public_speech=extract_public_text(response), private_thought=private_thought
    )
    return normalize_speech_decision(decision, raw_fallback=response)
