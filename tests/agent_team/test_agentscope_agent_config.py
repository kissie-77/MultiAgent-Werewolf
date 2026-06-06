"""AgentScopeWerewolfAgent 主实现的测试。"""

import pytest

from llm_werewolf.strategy.contracts.decisions import WitchNightDecision
from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent


class _ContentOnlyMsg:
    def __init__(self, content: str):
        self.content = content
        self.metadata = None


class _ContentJsonAgent:
    def __call__(self, *_args: object, **_kwargs: object) -> _ContentOnlyMsg:
        return _ContentOnlyMsg('{"action":"save","seat":0,"reason":"救今晚刀口"}')


class _ToolChoiceRejectingAgent:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, *_args: object, **kwargs: object) -> _ContentOnlyMsg:
        if "structured_model" in kwargs:
            self.calls.append("structured")
            raise RuntimeError("Thinking mode does not support this tool_choice")
        self.calls.append("plain")
        return _ContentOnlyMsg('{"action":"save","seat":0,"reason":"工具调用被拒绝后仍救刀口"}')


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


@pytest.mark.asyncio
async def test_get_structured_response_recovers_content_json_without_metadata() -> None:
    agent = AgentScopeWerewolfAgent(name="Witch", model="deepseek-v4-flash")
    agent.agentscope_agent = _ContentJsonAgent()

    decision = await agent.get_structured_response("女巫夜晚行动", WitchNightDecision)

    assert isinstance(decision, WitchNightDecision)
    assert decision.action == "save"
    assert decision.seat == 0
    assert agent.chat_history[-1]["content"] == decision.model_dump_json()


@pytest.mark.asyncio
async def test_get_structured_response_retries_plain_when_tool_choice_unsupported() -> None:
    backend = _ToolChoiceRejectingAgent()
    agent = AgentScopeWerewolfAgent(name="Witch", model="deepseek-v4-flash")
    agent.agentscope_agent = backend

    decision = await agent.get_structured_response("女巫夜晚行动", WitchNightDecision)

    assert isinstance(decision, WitchNightDecision)
    assert decision.action == "save"
    assert decision.seat == 0
    assert backend.calls == ["structured", "plain"]
