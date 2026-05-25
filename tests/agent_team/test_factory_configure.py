"""AgentScope 后置配置连线（configure_agents_for_players）的测试。"""

from unittest.mock import MagicMock, patch

from llm_werewolf.agent_team import factory
from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent
from llm_werewolf.agent_team.factory import configure_agents_for_players
from llm_werewolf.game_runtime.config import PlayerConfig
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
        configure_agents_for_players([player], default_plan="default")

    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["show_console_output"] is False
    assert agent.game_role_name == "Seer"
    assert agent.number == 3
    assert agent.agentscope_agent is mock_create.return_value


def test_configure_agents_skips_agents_without_configure_role() -> None:
    from llm_werewolf.agent_team.base import DemoAgent

    agent = DemoAgent(name="P1")
    player = Player("player_1", "P1", Seer, agent=agent, ai_model="demo")

    configure_agents_for_players([player], default_plan="default")
    assert not hasattr(agent, "agentscope_agent") or agent.agentscope_agent is None  # noqa: SLF001


def test_agent_uses_structured_output_requires_react_backend() -> None:
    from llm_werewolf.agent_team.structured_invoke import agent_uses_structured_output

    agent = AgentScopeWerewolfAgent(name="P1")
    assert agent_uses_structured_output(agent) is False

    agent.agentscope_agent = MagicMock()
    assert agent_uses_structured_output(agent) is True


def test_create_react_agent_disables_agentscope_console_output(monkeypatch) -> None:
    class FakeReActAgent:
        def __init__(
            self,
            *,
            name,
            sys_prompt,
            model,
            formatter,
            toolkit,
            memory,
            print_hint_msg,
        ) -> None:
            self.name = name
            self.sys_prompt = sys_prompt
            self.model = model
            self.formatter = formatter
            self.toolkit = toolkit
            self.memory = memory
            self.print_hint_msg = print_hint_msg
            self.console_output_enabled = None
            self._disable_console_output = False

        def set_console_output_enabled(self, enabled: bool) -> None:
            self.console_output_enabled = enabled
            self._disable_console_output = not enabled

    monkeypatch.setenv("TEST_LLM_API_KEY", "test-key")
    monkeypatch.setattr(factory, "OpenAIChatModel", lambda **_kwargs: object())
    monkeypatch.setattr(factory, "OpenAIChatFormatter", object)
    monkeypatch.setattr(factory, "Toolkit", object)
    monkeypatch.setattr(factory, "InMemoryMemory", object)
    monkeypatch.setattr(factory, "ReActAgent", FakeReActAgent)

    config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="TEST_LLM_API_KEY",
    )

    agent = factory.create_react_agent(
        config,
        agent_name="P1",
        sys_prompt="system",
    )

    assert agent.print_hint_msg is False
    assert agent.console_output_enabled is False
    assert agent._disable_console_output is True


def test_configure_agents_can_enable_raw_agentscope_console_output() -> None:
    config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    agent = AgentScopeWerewolfAgent(name="P1", player_config=config)
    player = Player("player_3", "P1", Seer, agent=agent, ai_model="gpt-test")

    with patch("llm_werewolf.agent_team.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        configure_agents_for_players(
            [player],
            default_plan="default",
            show_agent_raw=True,
        )

    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["show_console_output"] is True


def test_create_react_agent_enables_agentscope_console_output(monkeypatch) -> None:
    class FakeReActAgent:
        def __init__(
            self,
            *,
            name,
            sys_prompt,
            model,
            formatter,
            toolkit,
            memory,
            print_hint_msg,
        ) -> None:
            self.name = name
            self.sys_prompt = sys_prompt
            self.model = model
            self.formatter = formatter
            self.toolkit = toolkit
            self.memory = memory
            self.print_hint_msg = print_hint_msg
            self.console_output_enabled = None
            self._disable_console_output = True

        def set_console_output_enabled(self, enabled: bool) -> None:
            self.console_output_enabled = enabled
            self._disable_console_output = not enabled

    monkeypatch.setenv("TEST_LLM_API_KEY", "test-key")
    monkeypatch.setattr(factory, "OpenAIChatModel", lambda **_kwargs: object())
    monkeypatch.setattr(factory, "OpenAIChatFormatter", object)
    monkeypatch.setattr(factory, "Toolkit", object)
    monkeypatch.setattr(factory, "InMemoryMemory", object)
    monkeypatch.setattr(factory, "ReActAgent", FakeReActAgent)

    config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="TEST_LLM_API_KEY",
    )

    agent = factory.create_react_agent(
        config,
        agent_name="P1",
        sys_prompt="system",
        show_console_output=True,
    )

    assert agent.console_output_enabled is True
    assert agent._disable_console_output is False
