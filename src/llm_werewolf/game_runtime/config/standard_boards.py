"""Canonical match board sizes and config_id naming."""

from __future__ import annotations

STANDARD_BOARD_SIZES: tuple[int, ...] = (4, 6, 8, 12, 16)


def standard_config_id(player_count: int) -> str:
    if player_count not in STANDARD_BOARD_SIZES:
        msg = f"Unsupported standard board size: {player_count}; use one of {STANDARD_BOARD_SIZES}"
        raise ValueError(msg)
    return f"standard-{player_count}p"


def standard_config_path(player_count: int) -> str:
    return f"configs/{standard_config_id(player_count)}.yaml"
