"""AgentScopeWerewolfAgent 主实现的测试。"""

import pytest

from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent


def test_agentscope_agent_configure_role() -> None:
    agent = AgentScopeWerewolfAgent(name="P1", plan="稳健")
    agent.configure_role(seat_number=5, game_role_name="Seer", plan_text="稳健")
    assert agent.game_role_name == "Seer"
    assert agent.number == 5
    assert len(agent.chat_history) == 1
    assert "预言家" in agent.chat_history[0]["content"]


@pytest.mark.asyncio
async def test_get_response_requires_agentscope_backend() -> None:
    agent = AgentScopeWerewolfAgent(name="P1")
    agent.configure_role(seat_number=2, game_role_name="Seer", plan_text="稳健")
    with pytest.raises(RuntimeError, match="AgentScope backend not initialized"):
        await agent.get_response("【行动】预言家：请选择目标\n可选目标：\n1. A")


def test_extract_helpers() -> None:
    agent = AgentScopeWerewolfAgent(name="P1")
    assert agent.extract_target("回复 [[7]]") == 7
    long_speech = "我觉得三号玩家昨晚的票型非常可疑需要重点留意"
    assert len(long_speech) >= 15
    assert agent.extract_content(f"[[{long_speech}]]") == long_speech
