"""Shared fallback helpers for failed target decisions."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


@dataclass(frozen=True)
class TargetFallbackResult:
    target: PlayerProtocol | None
    used_random: bool
    reason: str | None = None


def select_target_fallback(
    possible_targets: list[PlayerProtocol],
    *,
    allow_random: bool,
    reason: str,
) -> TargetFallbackResult:
    """Resolve a failed target decision through the configured fallback policy."""
    if not allow_random or not possible_targets:
        return TargetFallbackResult(target=None, used_random=False)

    normalized_reason = reason.strip() or "decision_failed"
    target = random.choice(possible_targets)  # noqa: S311
    return TargetFallbackResult(target=target, used_random=True, reason=normalized_reason)
