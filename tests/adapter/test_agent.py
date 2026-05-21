"""Tests for adapter/agent.py."""

import pytest

from llm_werewolf.adapter.agent import AgentScopeWerewolfAgent
from llm_werewolf.core.roles import Seer


def test_agentscope_agent_bind_role() -> None:
    agent = AgentScopeWerewolfAgent(name="P1", plan="稳健")
    agent.bind_role(Seer, seat_number=5)
    assert agent.role_definition is not None
    assert agent.role_definition.name == "Seer"  # type: ignore[union-attr]
    assert len(agent.chat_history) == 2
    assert "【系统提示】" in agent.chat_history[0]["content"]
    assert "预言家" in agent.chat_history[1]["content"]


@pytest.mark.asyncio
async def test_direct_model_fallback() -> None:
    agent = AgentScopeWerewolfAgent(name="P1")
    agent.bind_role(Seer, seat_number=2)
    response = await agent.get_response("【行动】预言家：请选择目标\n可选目标：\n1. A")
    assert "[[" in response


def test_extract_helpers() -> None:
    agent = AgentScopeWerewolfAgent(name="P1")
    assert agent.extract_target("回复 [[7]]") == 7
    assert agent.extract_content("[[你好]]") == "你好"
