from pathlib import Path

import pytest

from llm_werewolf.interface.modes import list_modes, resolve_config_path


def test_explicit_config_overrides_mode() -> None:
    assert resolve_config_path("configs/custom.yaml") == Path("configs/custom.yaml")


def test_default_mode_resolves_main_agentscope_config() -> None:
    assert resolve_config_path() == Path("configs/llm-12p-agentscope.yaml")


def test_list_modes_contains_basic_badge_and_extended() -> None:
    rules = {mode.rules for mode in list_modes()}
    assert {"basic", "badge_flow", "extended_roles"} <= rules


def test_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported mode"):
        resolve_config_path(participation="human_mixed", rules="basic")
