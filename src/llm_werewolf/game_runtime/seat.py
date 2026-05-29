"""Runtime helpers for stable player seat numbers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


def get_player_seat(player: PlayerProtocol) -> int | None:
    """Return the stable 1-based seat number encoded in player id or name."""
    for value in (player.player_id, player.name):
        match = re.search(r"(\d+)$", str(value))
        if match:
            return int(match.group(1))
    return None


def resolve_player_by_seat(seat: int, candidates: list[PlayerProtocol]) -> PlayerProtocol | None:
    """Find a candidate by its stable seat number."""
    for player in candidates:
        if get_player_seat(player) == seat:
            return player
    return None
