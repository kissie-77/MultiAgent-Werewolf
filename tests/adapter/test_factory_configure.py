"""Tests for AgentScope post-setup wiring (configure_agents_for_players)."""

from unittest.mock import MagicMock, patch

import pytest

from llm_werewolf.adapter.factory import configure_agents_for_players
from llm_werewolf.core.config import PlayerConfig
from llm_werewolf.core.player import Player
from llm_werewolf.core.roles.villager import Seer
from llm_werewolf.integration.agentscope import AgentScopeWerewolfAgent


def test_configure_agents_calls_configure_role_on_integration_agent() -> None:
    config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="OPENAI_API_KEY",
        plan="bold",
    )
    agent = AgentScopeWerewolfAgent(
        name="P1",
        player_config=config,
        plan_name="bold",
    )
    player = Player("player_3", "P1", Seer, agent=agent, ai_model="gpt-test")

    with patch("llm_werewolf.adapter.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        configure_agents_for_players([player], default_plan="default")

    mock_create.assert_called_once()
    assert agent.game_role_name == "Seer"
    assert agent.number == 3
    assert agent.agentscope_agent is mock_create.return_value


def test_configure_agents_skips_agents_without_configure_role() -> None:
    from llm_werewolf.agents.base import LLMAgent

    agent = LLMAgent(
        name="P1",
        model="gpt-test",
        api_key="sk-test",
        base_url="https://example.com/v1",
    )
    player = Player("player_1", "P1", Seer, agent=agent, ai_model="gpt-test")

    configure_agents_for_players([player], default_plan="default")
    assert not hasattr(agent, "agentscope_agent") or agent.agentscope_agent is None  # noqa: SLF001


def test_agent_uses_structured_output_disabled_for_kissie_prompt_track() -> None:
    from llm_werewolf.adapter.structured_invoke import agent_uses_structured_output

    agent = AgentScopeWerewolfAgent(name="P1")
    assert agent_uses_structured_output(agent) is False

    agent.agentscope_agent = MagicMock()
    assert agent_uses_structured_output(agent) is False
