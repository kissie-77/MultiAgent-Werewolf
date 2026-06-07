"""Legacy engine-driven /state parity test (removed with state/view services)."""

from __future__ import annotations

import pytest


@pytest.mark.skip(
    reason="interface.api.services.state/view removed; use replay snapshot tests instead",
)
def test_live_state_matches_disk_state_midgame() -> None:
    """Placeholder so collection stays green until a replay-based parity test lands."""
