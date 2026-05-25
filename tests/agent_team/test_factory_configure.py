"""AgentScope 后置配置连线（configure_agents_for_players）的测试。"""

from unittest.mock import MagicMock, patch

from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent
from llm_werewolf.agent_team.factory import configure_agents_for_players
from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.game_runtime.events import EventLogger
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Seer


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

    with patch("llm_werewolf.agent_team.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        player.game_state = MagicMock(event_logger=EventLogger())
        configure_agents_for_players([player], default_plan="default")

    mock_create.assert_called_once()
    assert agent.game_role_name == "Seer"
    assert agent.number == 3
    assert agent.agentscope_agent is mock_create.return_value
    assert agent.memory_manager is not None
    assert agent.memory_manager.player_id == "player_3"
    assert agent.memory_manager.role == "prophet"
    assert agent.memory_manager.plan_name == "bold"


def test_configure_agents_skips_agents_without_configure_role() -> None:
    from llm_werewolf.agent_team.base import DemoAgent

    agent = DemoAgent(name="P1")
    player = Player("player_1", "P1", Seer, agent=agent, ai_model="demo")
    player.game_state = MagicMock(event_logger=EventLogger())

    configure_agents_for_players([player], default_plan="default")
    assert not hasattr(agent, "agentscope_agent") or agent.agentscope_agent is None  # noqa: SLF001


def test_agent_uses_structured_output_requires_react_backend() -> None:
    from llm_werewolf.agent_team.structured_invoke import agent_uses_structured_output

    agent = AgentScopeWerewolfAgent(name="P1")
    assert agent_uses_structured_output(agent) is False

    agent.agentscope_agent = MagicMock()
    assert agent_uses_structured_output(agent) is True
