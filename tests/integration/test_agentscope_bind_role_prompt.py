"""Tests for collaborator-facing bind_role_prompt on AgentScope agent."""

from unittest.mock import MagicMock, patch

from llm_werewolf.core.config import PlayerConfig
from llm_werewolf.integration.agentscope import AgentScopeWerewolfAgent


def test_bind_role_prompt_delegates_to_configure_role() -> None:
    config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    agent = AgentScopeWerewolfAgent(name="P1", player_config=config, plan="default")

    with patch("llm_werewolf.adapter.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock()
        agent.bind_role_prompt("Seer", seat_number=4, plan="bold")

    assert agent.game_role_name == "Seer"
    assert agent.number == 4
    assert agent.plan == "bold"
    mock_create.assert_called_once()
