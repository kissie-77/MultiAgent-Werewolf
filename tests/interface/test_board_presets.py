"""Custom role lineup for web start and preset catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_werewolf.game_runtime.config.player_config import PlayersConfig
from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.api.models.actions import StartGameRequest
from llm_werewolf.interface.api.services.board_preset_catalog import build_board_presets_response
from llm_werewolf.interface.cli.runtime.bootstrap import prepare_game_roster


def test_prepare_game_roster_uses_yaml_role_names() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        role_names=["Werewolf", "Werewolf", "Seer", "Witch", "Hunter", "Villager"],
        players=[
            {"name": f"P{i}", "model": "demo"} for i in range(1, 7)
        ],
    )
    _players, _roles, game_config = prepare_game_roster(cfg)
    assert game_config.role_names == cfg.role_names


def test_start_request_infers_player_count_from_role_names() -> None:
    req = StartGameRequest(
        config_id="standard-6p",
        role_names=["Werewolf", "Werewolf", "Seer", "Witch", "Magician", "Raven"],
    )
    assert req.player_count == 6


_CONFIGS = Path(__file__).resolve().parents[2] / "configs"


def test_preset_yaml_loads_with_role_names() -> None:
    path = _CONFIGS / "preset-lovers-9.yaml"
    if not path.is_file():
        pytest.skip("preset file missing")
    cfg = load_config(path)
    assert cfg.role_names is not None
    assert len(cfg.role_names) == 9
    assert "Cupid" in cfg.role_names


def test_board_preset_catalog_lists_curated() -> None:
    resp = build_board_presets_response(_CONFIGS)
    curated = [p for p in resp.presets if p.kind == "curated"]
    assert len(curated) >= 3
    assert len(resp.roles) >= 20
    lovers = next((p for p in curated if p.preset_id == "preset-lovers-9"), None)
    assert lovers is not None
    assert lovers.player_count == 9
    assert "Cupid" in lovers.role_names
