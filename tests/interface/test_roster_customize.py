"""Tests for start-game roster customization."""

from __future__ import annotations

import pytest

from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.api.models.actions import PlayerRosterSlot, StartGameRequest
from llm_werewolf.interface.api.services.roster_customize import (
    apply_roster_customizations,
    has_roster_customizations,
    prepare_start_players_config,
)


@pytest.fixture
def demo_config(tmp_path):
    from tests.interface.fixtures import write_demo_config

    configs_dir = tmp_path / "configs"
    path = write_demo_config(configs_dir)
    return load_config(path)


def test_apply_player_count_and_names(demo_config) -> None:
    updated = apply_roster_customizations(
        demo_config,
        player_count=8,
        players=[PlayerRosterSlot(name="Alpha"), PlayerRosterSlot(name="Beta")],
    )
    assert len(updated.players) == 8
    assert updated.players[0].name == "Alpha"
    assert updated.players[1].name == "Beta"


def test_apply_human_seats(demo_config) -> None:
    updated = apply_roster_customizations(demo_config, human_seats=[1, 3])
    assert updated.players[0].model == "human"
    assert updated.players[2].model == "human"
    assert updated.players[1].model == "demo"


def test_prepare_start_players_config_returns_none_without_overrides(demo_config) -> None:
    request = StartGameRequest(config_id="demo-6")
    assert has_roster_customizations(request) is False
    assert prepare_start_players_config(demo_config, request) is None


def test_roster_slot_applies_api_key_and_temperature():
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig, PlayersConfig
    from llm_werewolf.interface.api.models.actions import PlayerRosterSlot
    from llm_werewolf.interface.api.services.roster_customize import apply_roster_customizations

    base = PlayersConfig(
        language="zh-CN",
        players=[
            PlayerConfig(name=f"P{i}", model="demo") for i in range(1, 7)
        ],
    )
    slots = [
        PlayerRosterSlot(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-seat1",
            temperature=1.1,
        )
    ] + [PlayerRosterSlot() for _ in range(5)]

    result = apply_roster_customizations(base, players=slots)
    assert result.players[0].api_key == "sk-seat1"
    assert result.players[0].temperature == 1.1
    assert result.players[0].model == "deepseek-chat"
