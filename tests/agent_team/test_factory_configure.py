"""AgentScope 后置配置连线（configure_agents_for_players）的测试。"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from llm_werewolf.game_runtime.config import MemoryConfig, PlanAssignmentConfig, PlayerConfig
from llm_werewolf.agent_team.agents.factory import (
    _build_compressor,
    assign_role_plan_names,
    configure_agents_for_players,
    _register_no_thinking_print_hook,
    _wrap_memory_add_without_thinking,
    _disable_agentscope_console_output,
    _register_structured_tool_reply_completion_hook,
)
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.events.events import EventLogger
from llm_werewolf.game_runtime.roles.villager import Seer, Villager, Witch
from llm_werewolf.game_runtime.roles.werewolf import Werewolf
from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent


def test_configure_agents_calls_configure_role_on_integration_agent() -> None:
    config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="OPENAI_API_KEY",
        plan="bold",
    )
    agent = AgentScopeWerewolfAgent(name="P1", player_config=config, plan_name="bold")
    player = Player("player_3", "P1", Seer, agent=agent, ai_model="gpt-test")

    with patch("llm_werewolf.agent_team.agents.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        configure_agents_for_players([player], default_plan="default", event_logger=EventLogger())

    mock_create.assert_called_once()
    assert agent.game_role_name == "Seer"
    assert agent.number == 3
    assert agent.agentscope_agent is mock_create.return_value
    assert agent.memory_manager is not None
    assert agent.memory_manager.player_id == "player_3"
    assert agent.memory_manager.role == "prophet"
    assert agent.memory_manager.plan_name == "bold"


def _agentscope_player(player_id: str, name: str, role_class: type, plan: str | None = None):
    config = PlayerConfig(
        name=name,
        model="gpt-test",
        base_url="https://example.com/v1",
        api_key_env="OPENAI_API_KEY",
        plan=plan,
    )
    agent = AgentScopeWerewolfAgent(
        name=name,
        player_config=config,
        plan_name=plan or "default",
    )
    return Player(player_id, name, role_class, agent=agent, ai_model="gpt-test")


def test_assign_role_plan_names_respects_manual_player_plan() -> None:
    players = [
        _agentscope_player("player_1", "P1", Werewolf, plan="wolf_aggressive"),
        _agentscope_player("player_2", "P2", Werewolf),
        _agentscope_player("player_3", "P3", Werewolf),
    ]
    plan_assignment = PlanAssignmentConfig(
        enabled=True,
        mode="role_cycle",
        role_plans={"wolf": ["wolf_conservative", "wolf_skeptical"]},
    )

    assignments = assign_role_plan_names(
        players, default_plan="default", plan_assignment=plan_assignment
    )

    assert "player_1" not in assignments
    assert assignments == {
        "player_2": "wolf_conservative",
        "player_3": "wolf_skeptical",
    }


def test_assign_role_plan_names_random_mode_is_seeded() -> None:
    players = [
        _agentscope_player("player_1", "P1", Werewolf),
        _agentscope_player("player_2", "P2", Werewolf),
        _agentscope_player("player_3", "P3", Werewolf),
    ]
    plan_assignment = PlanAssignmentConfig(enabled=True, mode="role_random", seed=13)

    first = assign_role_plan_names(
        players, default_plan="default", plan_assignment=plan_assignment
    )
    second = assign_role_plan_names(
        players, default_plan="default", plan_assignment=plan_assignment
    )

    assert first == second
    assert set(first.values()).issubset(
        {
            "wolf_conservative",
            "wolf_aggressive",
            "wolf_skeptical",
            "wolf_coordinator",
        }
    )


def test_configure_agents_uses_assigned_role_plan_text() -> None:
    player = _agentscope_player("player_1", "P1", Werewolf)
    plan_assignment = PlanAssignmentConfig(
        enabled=True,
        mode="role_cycle",
        role_plans={"wolf": ["wolf_skeptical"]},
    )

    with patch("llm_werewolf.agent_team.agents.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        configure_agents_for_players(
            [player],
            default_plan="default",
            plan_assignment=plan_assignment,
            event_logger=EventLogger(),
        )

    assert "狼人质疑派打法" in player.agent.plan
    assert player.agent.memory_manager.plan_name == "wolf_skeptical"


def test_configure_agents_injects_current_role_pool_into_system_prompt() -> None:
    players = [
        _agentscope_player("player_1", "P1", Werewolf),
        _agentscope_player("player_2", "P2", Werewolf),
        _agentscope_player("player_3", "P3", Seer),
        _agentscope_player("player_4", "P4", Witch),
        _agentscope_player("player_5", "P5", Villager),
        _agentscope_player("player_6", "P6", Villager),
    ]

    with patch("llm_werewolf.agent_team.agents.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        configure_agents_for_players(players, default_plan="default", event_logger=EventLogger())

    prompt = mock_create.call_args.kwargs["sys_prompt"]
    assert "【本局角色池】" in prompt
    assert "Werewolf x2" in prompt
    assert "Villager x2" in prompt
    assert "Seer x1" in prompt
    assert "Witch x1" in prompt
    assert "Guard x" not in prompt
    assert "如果长期策略、经验或示例提到未出现在本局角色池的身份" in prompt
    assert prompt.rstrip().endswith("如果长期策略、经验或示例提到未出现在本局角色池的身份，本局忽略这些身份。")


def test_configure_agents_injects_current_role_pool_into_working_memory() -> None:
    players = [
        _agentscope_player("player_1", "P1", Werewolf),
        _agentscope_player("player_2", "P2", Werewolf),
        _agentscope_player("player_3", "P3", Seer),
        _agentscope_player("player_4", "P4", Witch),
        _agentscope_player("player_5", "P5", Villager),
        _agentscope_player("player_6", "P6", Villager),
    ]

    with patch("llm_werewolf.agent_team.agents.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        configure_agents_for_players(players, default_plan="default", event_logger=EventLogger())

    context = players[0].agent.memory_manager.get_context_for_decision()
    assert "【本局固定信息】" in context
    assert "【本局角色池】" in context
    assert "Werewolf x2" in context
    assert "Guard x" not in context


def test_configure_agents_binds_demo_agent_role() -> None:
    from llm_werewolf.agent_team.agents.base import DemoAgent

    agent = DemoAgent(name="P1")
    player = Player("player_1", "P1", Seer, agent=agent, ai_model="demo")

    configure_agents_for_players([player], default_plan="default", event_logger=EventLogger())

    assert agent.seat_number == 1
    assert agent.role_definition is not None
    assert agent.chat_history


def test_configure_agents_passes_player_count_to_agentscope_agent() -> None:
    players = [
        _agentscope_player(
            f"player_{seat}",
            f"P{seat}",
            Werewolf if seat <= 4 else Seer,
        )
        for seat in range(1, 14)
    ]

    with patch("llm_werewolf.agent_team.agents.factory.create_react_agent") as mock_create:
        mock_create.return_value = MagicMock(name="ReActAgent")
        configure_agents_for_players(players, default_plan="default", event_logger=EventLogger())

    assert all(player.agent.player_count == 13 for player in players)


def test_agent_uses_structured_output_requires_react_backend() -> None:
    from llm_werewolf.agent_team.invocation.structured_invoke import agent_uses_structured_output

    agent = AgentScopeWerewolfAgent(name="P1")
    assert agent_uses_structured_output(agent) is False

    agent.agentscope_agent = MagicMock()
    assert agent_uses_structured_output(agent) is True


def test_build_compressor_does_not_inherit_player_base_url(monkeypatch) -> None:
    monkeypatch.setenv("PLAYER_API_KEY", "test-key")
    player_config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://token-plan-sgp.xiaomimimo.com/anthropic",
        api_key_env="PLAYER_API_KEY",
    )
    memory_config = MemoryConfig(working_compression_base_url="")

    compressor = _build_compressor(memory_config, player_config)

    assert compressor is None


def test_build_compressor_reuses_player_api_key_with_explicit_memory_base_url(monkeypatch) -> None:
    monkeypatch.setenv("PLAYER_API_KEY", "test-key")
    player_config = PlayerConfig(
        name="P1",
        model="gpt-test",
        base_url="https://token-plan-sgp.xiaomimimo.com/anthropic",
        api_key_env="PLAYER_API_KEY",
    )
    memory_config = MemoryConfig(
        working_compression_base_url="https://token-plan-sgp.xiaomimimo.com/v1",
        working_compression_model="mimo-v2.5-pro",
    )

    compressor = _build_compressor(memory_config, player_config)

    assert compressor is not None
    assert compressor._api_key == "test-key"
    assert compressor._base_url == "https://token-plan-sgp.xiaomimimo.com/v1"
    assert compressor._model == "mimo-v2.5-pro"


def test_register_no_thinking_print_hook_strips_thinking_blocks() -> None:
    registered: dict[str, object] = {}

    class DummyAgent:
        def register_instance_hook(self, hook_type: str, hook_name: str, hook) -> None:
            registered["hook_type"] = hook_type
            registered["hook_name"] = hook_name
            registered["hook"] = hook

    agent = DummyAgent()

    returned = _register_no_thinking_print_hook(agent)

    assert returned is agent
    assert registered["hook_type"] == "pre_print"
    assert registered["hook_name"] == "strip_thinking_blocks"

    msg = SimpleNamespace(
        content=[
            {"type": "thinking", "thinking": "internal reasoning"},
            {"type": "text", "text": "公开发言"},
        ]
    )
    kwargs = {"msg": msg, "last": True, "speech": None}

    sanitized = registered["hook"](None, kwargs)

    assert sanitized["msg"].content == [{"type": "text", "text": "公开发言"}]


@pytest.mark.asyncio
async def test_wrap_memory_add_without_thinking_strips_blocks_before_store() -> None:
    recorded: list[object] = []

    class DummyMemory:
        async def add(self, msg, *args, **kwargs) -> None:
            del args, kwargs
            recorded.append(msg)

    class DummyAgent:
        def __init__(self) -> None:
            self.memory = DummyMemory()

        def register_instance_hook(self, hook_type: str, hook_name: str, hook) -> None:
            del hook_type, hook_name, hook

    agent = DummyAgent()
    _wrap_memory_add_without_thinking(agent)

    msg = SimpleNamespace(
        content=[
            {"type": "thinking", "thinking": "internal reasoning"},
            {"type": "text", "text": "公开发言"},
        ]
    )

    await agent.memory.add(msg)

    assert len(recorded) == 1
    assert recorded[0].content == [{"type": "text", "text": "公开发言"}]


def test_disable_agentscope_console_output_sets_internal_flag() -> None:
    class DummyAgent:
        def __init__(self) -> None:
            self._disable_console_output = False

    agent = DummyAgent()

    returned = _disable_agentscope_console_output(agent)

    assert returned is agent
    assert agent._disable_console_output is True


def test_structured_tool_reply_completion_hook_adds_terminal_text() -> None:
    registered: dict[str, object] = {}

    class DummyAgent:
        finish_function_name = "generate_response"
        _required_structured_model = object()

        def register_instance_hook(self, hook_type: str, hook_name: str, hook) -> None:
            registered["hook_type"] = hook_type
            registered["hook_name"] = hook_name
            registered["hook"] = hook

    class DummyMsg:
        def __init__(self) -> None:
            self.content = [{"type": "tool_use", "name": "generate_response", "id": "call_1"}]

        def get_content_blocks(self, block_type: str):
            return [block for block in self.content if block.get("type") == block_type]

    agent = DummyAgent()
    _register_structured_tool_reply_completion_hook(agent)
    msg = DummyMsg()

    result = registered["hook"](agent, {}, msg)

    assert registered["hook_type"] == "post_reasoning"
    assert registered["hook_name"] == "complete_structured_generate_response_reply"
    assert result is msg
    assert msg.content[-1] == {"type": "text", "text": "Structured response submitted."}


def test_structured_tool_reply_completion_hook_ignores_non_structured_turn() -> None:
    registered: dict[str, object] = {}

    class DummyAgent:
        finish_function_name = "generate_response"
        _required_structured_model = None

        def register_instance_hook(self, hook_type: str, hook_name: str, hook) -> None:
            del hook_type, hook_name
            registered["hook"] = hook

    class DummyMsg:
        content = [{"type": "tool_use", "name": "generate_response", "id": "call_1"}]

        def get_content_blocks(self, block_type: str):
            return [block for block in self.content if block.get("type") == block_type]

    agent = DummyAgent()
    _register_structured_tool_reply_completion_hook(agent)

    assert registered["hook"](agent, {}, DummyMsg()) is None
