"""Shared seat-id parsing for /state, /view, and the session manager.

A single source of truth for turning a ``player_N`` id into its 1-based seat
number, so the same id never yields different results across response paths.
"""

from __future__ import annotations


def seat_of(player_id: str | None) -> int | None:
    """Parse the 1-based seat number out of a ``player_N`` id.

    Returns ``None`` for a falsy id or any id whose trailing segment is not an
    integer (rather than raising), so callers can filter unparseable ids.
    """
    if not player_id:
        return None
    try:
        return int(str(player_id).rsplit("_", 1)[-1])
    except (ValueError, IndexError, AttributeError):
        return None
