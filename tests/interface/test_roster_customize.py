"""Tests for start-game roster customization."""

from __future__ import annotations

import pytest

from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.api.models.actions import (
    PlayerRosterDefaults,
    PlayerRosterSlot,
    StartGameRequest,
)
from llm_werewolf.interface.api.services.roster_customize import (
    has_roster_customizations,
    apply_roster_customizations,
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
    request = StartGameRequest(config_id="standard-6p")
    assert has_roster_customizations(request) is False
    assert prepare_start_players_config(demo_config, request) is None


def test_apply_provider_defaults(demo_config) -> None:
    updated = apply_roster_customizations(
        demo_config,
        defaults=PlayerRosterDefaults(provider="deepseek"),
    )
    llm = next(p for p in updated.players if p.model != "human")
    assert llm.api_key_env == "DEEPSEEK_API_KEY"
    assert llm.base_url == "https://api.deepseek.com/v1"


def test_apply_provider_per_seat(demo_config) -> None:
    updated = apply_roster_customizations(
        demo_config,
        players=[
            PlayerRosterSlot(provider="doubao"),
            PlayerRosterSlot(provider="openai"),
        ],
    )
    assert updated.players[0].api_key_env == "ARK_API_KEY"
    assert updated.players[0].model_env == "ARK_EP"
    assert updated.players[1].api_key_env == "OPENAI_API_KEY"


def test_defaults_provider_counts_as_customization() -> None:
    request = StartGameRequest(config_id="standard-6p", defaults=PlayerRosterDefaults(provider="doubao"))
    assert has_roster_customizations(request) is True
