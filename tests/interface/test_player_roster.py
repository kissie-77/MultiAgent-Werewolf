from pathlib import Path

import pytest

from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.game_runtime.config import (
    PlayerConfig,
    PlayersConfig,
    PlayerRosterConfig,
    PlayerTemplateConfig,
)
from llm_werewolf.interface.player_roster import resolve_participation, resolve_player_configs


def _deepseek_template() -> PlayerTemplateConfig:
    return PlayerTemplateConfig(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
    )


def _six_demo_players() -> list[PlayerConfig]:
    return [PlayerConfig(name=f"P{i}", model="demo") for i in range(1, 7)]


def test_resolve_all_agent_roster_from_template_count() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        player_roster=PlayerRosterConfig(
            count=9,
            mode="all_agent",
            llm_template=_deepseek_template(),
        ),
    )

    players = resolve_player_configs(cfg)

    assert len(players) == 9
    assert [player.name for player in players] == [f"Player{i}" for i in range(1, 10)]
    assert {player.model for player in players} == {"deepseek-v4-flash"}
    assert {player.api_key_env for player in players} == {"DEEPSEEK_API_KEY"}


def test_resolve_human_mixed_roster_keeps_one_human() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        player_roster=PlayerRosterConfig(
            count=9,
            mode="human_mixed",
            human=PlayerConfig(name="HumanPlayer", model="human"),
            llm_template=_deepseek_template(),
        ),
    )

    players = resolve_player_configs(cfg)

    assert len(players) == 9
    assert players[0].name == "HumanPlayer"
    assert players[0].model == "human"
    assert [player.name for player in players[1:]] == [f"Player{i}" for i in range(2, 10)]


def test_num_players_overrides_roster_count() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        player_roster=PlayerRosterConfig(
            count=12,
            mode="all_agent",
            llm_template=_deepseek_template(),
        ),
    )

    players = resolve_player_configs(cfg, num_players=7)

    assert len(players) == 7
    assert players[-1].name == "Player7"


def test_num_players_override_requires_roster_for_explicit_players() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())

    with pytest.raises(ValueError, match="player_roster"):
        resolve_player_configs(cfg, num_players=7)


def test_resolve_participation_prefers_roster_mode() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        player_roster=PlayerRosterConfig(
            count=8,
            mode="human_mixed",
            human=PlayerConfig(name="HumanPlayer", model="human"),
            llm_template=_deepseek_template(),
        ),
    )

    assert resolve_participation(cfg, requested_participation="all_agent") == "human_mixed"


def test_deepseek_roster_configs_resolve_requested_counts() -> None:
    all_agent = load_config(Path("configs/llm-12p-deepseek.yaml"))
    human_mixed = load_config(Path("configs/human-mixed-deepseek.yaml"))

    assert len(resolve_player_configs(all_agent, num_players=9)) == 9

    human_players = resolve_player_configs(human_mixed, num_players=9)
    assert len(human_players) == 9
    assert human_players[0].model == "human"
    assert human_players[1].name == "Player2"
