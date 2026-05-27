"""面向协作者的 AgentScope agent 上 bind_role_prompt 的测试。"""

from unittest.mock import MagicMock, patch

from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent


def test_bind_role_prompt_delegates_to_configure_role() -> None:
    config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    agent = AgentScopeWerewolfAgent(name="P1", player_config=config, plan="default")

    with patch("llm_werewolf.agent_team.agents.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock()
        agent.bind_role_prompt("Seer", seat_number=4, plan="bold")

    assert agent.game_role_name == "Seer"
    assert agent.number == 4
    assert agent.plan == "bold"
    mock_create.assert_called_once()
