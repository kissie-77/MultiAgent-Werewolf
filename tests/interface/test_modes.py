from pathlib import Path

import pytest

from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.cli.runtime.modes import list_modes, resolve_config_path


def test_explicit_config_overrides_mode() -> None:
    assert resolve_config_path("configs/custom.yaml") == Path("configs/custom.yaml")


def test_default_mode_resolves_main_agentscope_config() -> None:
    assert resolve_config_path() == Path("configs/llm-12p-agentscope.yaml")


def test_list_modes_contains_basic_badge_and_extended() -> None:
    rules = {mode.rules for mode in list_modes()}
    assert {"basic", "badge_flow", "extended_roles"} <= rules


def test_human_mixed_basic_uses_llm_config_not_demo() -> None:
    assert resolve_config_path(participation="human_mixed", rules="basic") == Path(
        "configs/llm-12p-kimi.yaml"
    )


def test_builtin_mode_config_paths_exist() -> None:
    for mode in list_modes():
        assert mode.config_path.is_file(), mode


def test_human_mixed_extended_uses_current_kimi_vibe_config() -> None:
    assert resolve_config_path(participation="human_mixed", rules="extended_roles") == Path(
        "configs/llm-12p-kimi.yaml"
    )


def test_real_llm_modes_use_current_kimi_vibe_config() -> None:
    for rules in ("basic", "badge_flow", "extended_roles"):
        cfg = load_config(resolve_config_path(participation="all_agent", rules=rules))

        assert {player.model for player in cfg.players} == {"kimi-k2.5"}
        assert {player.base_url for player in cfg.players} == {"https://www.vibeapi.cn/v1"}
        assert {player.api_key_env for player in cfg.players} == {"VIBE_API_KEY"}
        assert all(player.reasoning_effort is None for player in cfg.players)


def test_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported mode"):
        resolve_config_path(participation="unknown", rules="basic")
