from unittest.mock import MagicMock

import pytest

from llm_werewolf.agent_team.base import DemoAgent, HumanAgent
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.interface.cli import _find_single_human_player, _run_main


def _player(player_id: str, name: str, agent):
    return Player(player_id, name, Villager, agent=agent, ai_model=agent.model)


def test_find_single_human_player_returns_only_human() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    bot = _player("player_2", "Bot", DemoAgent(name="Bot", model="demo"))
    game_state = MagicMock(players=[human, bot])

    assert _find_single_human_player(game_state) == human


def test_find_single_human_player_rejects_missing_human() -> None:
    bot = _player("player_2", "Bot", DemoAgent(name="Bot", model="demo"))
    game_state = MagicMock(players=[bot])

    with pytest.raises(ValueError, match="exactly one human"):
        _find_single_human_player(game_state)


def test_find_single_human_player_rejects_multiple_humans() -> None:
    first = _player("player_1", "Human1", HumanAgent(name="Human1", model="human"))
    second = _player("player_2", "Human2", HumanAgent(name="Human2", model="human"))
    game_state = MagicMock(players=[first, second])

    with pytest.raises(ValueError, match="exactly one human"):
        _find_single_human_player(game_state)


def test_run_main_exposes_raw_agent_output_flag(monkeypatch) -> None:
    captured = {}

    async def fake_main(config, *, participation, rules, show_agent_raw):
        captured["config"] = config
        captured["participation"] = participation
        captured["rules"] = rules
        captured["show_agent_raw"] = show_agent_raw

    monkeypatch.setattr("llm_werewolf.interface.cli.main", fake_main)

    _run_main(
        config="configs/llm-12p-deepseek.yaml",
        participation="human_mixed",
        rules="badge_flow",
        show_agent_raw=True,
    )

    assert captured == {
        "config": "configs/llm-12p-deepseek.yaml",
        "participation": "human_mixed",
        "rules": "badge_flow",
        "show_agent_raw": True,
    }
