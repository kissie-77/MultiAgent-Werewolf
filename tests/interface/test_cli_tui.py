"""TUI CLI entry smoke tests."""

from __future__ import annotations

from unittest.mock import patch

from llm_werewolf.interface.cli import tui as tui_mod


def test_tui_main_invokes_run_tui() -> None:
    with patch.object(tui_mod, "run_tui") as mock_run:
        tui_mod.main(participation="all_agent", rules="basic")
    mock_run.assert_called_once()


def test_tui_main_handles_invalid_players() -> None:
    with patch.object(tui_mod, "run_tui") as mock_run:
        tui_mod.main(participation="all_agent", rules="basic", players=3)
    mock_run.assert_not_called()


def test_tui_entry_is_callable() -> None:
    assert callable(tui_mod.entry)
