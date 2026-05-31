"""Import tests for thin compatibility shim modules."""

from __future__ import annotations

import importlib


def test_interface_shim_modules_import() -> None:
    modules = [
        "llm_werewolf.interface.cli",
        "llm_werewolf.interface.cli_overrides",
        "llm_werewolf.interface.eval_cli",
        "llm_werewolf.interface.finalize_run",
        "llm_werewolf.interface.modes",
        "llm_werewolf.interface.player_count",
        "llm_werewolf.interface.tui",
        "llm_werewolf.interface.vote_swing_cli",
    ]
    for name in modules:
        mod = importlib.import_module(name)
        assert mod is not None


def test_ui_styles_constants() -> None:
    from llm_werewolf.ui import styles

    assert styles.CAMP_COLORS["werewolf"] == "red"
    assert styles.STYLE_WEREWOLF.bold is True
    assert styles.get_camp_color("unknown") == "white"
    assert styles.get_status_color("unknown") == "white"
    assert styles.get_phase_color("unknown") == "white"
    assert "#player_panel" in styles.TUI_CSS
