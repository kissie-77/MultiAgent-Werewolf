"""AgentScopeWerewolfAgent 回退响应的测试。"""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent


@pytest.fixture
def wolf_agent() -> AgentScopeWerewolfAgent:
    return AgentScopeWerewolfAgent(name="W1", role="wolf", number=3)


@pytest.fixture
def villager_agent() -> AgentScopeWerewolfAgent:
    return AgentScopeWerewolfAgent(name="V1", role="villager", number=1)


class TestWerewolfPrivateFallback:
    def test_no_good_identity_in_wolf_night_chat(
        self, wolf_agent: AgentScopeWerewolfAgent
    ) -> None:
        prompt = "You are W1, a Werewolf.\nDiscuss with your fellow werewolves who should be eliminated tonight.\nAvailable targets: P4, P5, P12."
        for _ in range(20):
            text = wolf_agent._generate_fallback_response(prompt, "empty")
            assert "好人" not in text
            assert "狼人" not in text
            assert "我是" not in text
            assert "I am" not in text.lower()

    def test_wolf_team_marker_detected(self, wolf_agent: AgentScopeWerewolfAgent) -> None:
        assert wolf_agent._is_werewolf_private_chat("Werewolf team discussion:\nA: hi")


class TestPublicFallback:
    def test_no_role_reveal_on_day_speech(self, villager_agent: AgentScopeWerewolfAgent) -> None:
        prompt = "Share your thoughts.\nProvide a brief statement for discussion."
        for _ in range(20):
            text = villager_agent._generate_fallback_response(prompt, "err")
            assert "我是" not in text
            assert villager_agent.role_name not in text

    def test_public_fallback_ignores_private_role(self) -> None:
        prompt = "Share your thoughts.\nProvide a brief statement for discussion."
        risky_terms = {
            "Seer",
            "Prophet",
            "Witch",
            "Guard",
            "Hunter",
            "Werewolf",
            "验",
            "查验",
            "药",
            "守",
            "开枪",
            "刀",
        }
        for role in ["prophet", "witch", "guard", "hunter", "wolf"]:
            agent = AgentScopeWerewolfAgent(name="P1", role=role, number=1)
            for _ in range(20):
                text = agent._generate_fallback_response(prompt, "err")
                assert agent.role_name not in text
                assert all(term not in text for term in risky_terms)


class TestStructuredFallback:
    def test_yes_no(self, wolf_agent: AgentScopeWerewolfAgent) -> None:
        prompt = "Please respond with ONLY 'YES' or 'NO'."
        assert wolf_agent._generate_fallback_response(prompt, "x") in {
            "[[0]]",
            "[[1]]",
            "YES",
            "NO",
        }

    def test_numeric_target(self, wolf_agent: AgentScopeWerewolfAgent) -> None:
        prompt = (
            "You are a Werewolf.\nAvailable targets:\n1. P4\n2. P5\n"
            "Please select a target by responding with ONLY the number"
        )
        assert wolf_agent._generate_fallback_response(prompt, "x") in {"1", "2"}


class DummyStructuredDecision(BaseModel):
    action: str


class DummyResponse:
    def __init__(self, content, metadata=None) -> None:
        self.content = content
        self.metadata = metadata or {}


class DummyMemoryMsg:
    def __init__(self, msg_id: str, content) -> None:
        self.id = msg_id
        self.content = content


class DummyMemory:
    def __init__(self, messages: list[DummyMemoryMsg]) -> None:
        self.messages = messages
        self.deleted: list[str] = []

    async def get_memory(self, **kwargs):
        del kwargs
        return list(self.messages)

    async def delete(self, msg_ids: list[str]) -> int:
        self.deleted.extend(msg_ids)
        before = len(self.messages)
        self.messages = [msg for msg in self.messages if msg.id not in set(msg_ids)]
        return before - len(self.messages)


def test_sanitize_agentscope_response_msg_removes_thinking_blocks() -> None:
    response = DummyResponse([
        {"type": "thinking", "thinking": "internal reasoning"},
        {"type": "text", "text": "公开回复"},
        {"type": "tool_result", "output": "kept"},
    ])

    sanitized = AgentScopeWerewolfAgent._sanitize_agentscope_response_msg(response)

    assert sanitized is response
    assert sanitized.content == [
        {"type": "text", "text": "公开回复"},
        {"type": "tool_result", "output": "kept"},
    ]


@pytest.mark.asyncio
async def test_call_agentscope_agent_sanitizes_response_before_extract(monkeypatch) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    agent.agentscope_agent = object()
    response_msg = DummyResponse([
        {"type": "thinking", "thinking": "internal reasoning"},
        {"type": "text", "text": "我觉得先听4号发言，先看票型再判断。"},
    ])

    async def fake_serial_call(fn):
        del fn
        return response_msg

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call", fake_serial_call
    )

    response = await agent._call_agentscope_agent("请发言")

    assert "internal reasoning" not in response
    assert all(block.get("type") != "thinking" for block in response_msg.content)
    assert "internal reasoning" not in agent.chat_history[-1]["content"]


@pytest.mark.asyncio
async def test_get_structured_response_sanitizes_thinking_blocks(monkeypatch) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    agent.agentscope_agent = object()
    response = DummyResponse(
        [
            {"type": "thinking", "thinking": "internal reasoning"},
            {"type": "text", "text": "会被忽略，因为走 metadata"},
        ],
        metadata={"action": "vote"},
    )

    async def fake_serial_call(fn):
        del fn
        return response

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call", fake_serial_call
    )

    decision = await agent.get_structured_response("请输出结构化结果", DummyStructuredDecision)

    assert decision is not None
    assert decision.action == "vote"
    assert response.content == [{"type": "text", "text": "会被忽略，因为走 metadata"}]
    assert agent._last_structured_source == "metadata"


@pytest.mark.asyncio
async def test_get_structured_response_recovers_tool_use_input_without_metadata(monkeypatch) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    agent.agentscope_agent = object()
    response = DummyResponse(
        [
            {
                "type": "tool_use",
                "name": "generate_response",
                "id": "call_1",
                "input": {"action": "vote"},
            }
        ],
        metadata=None,
    )

    async def fake_serial_call(fn):
        del fn
        return response

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call", fake_serial_call
    )

    decision = await agent.get_structured_response("请输出结构化结果", DummyStructuredDecision)

    assert decision is not None
    assert decision.action == "vote"
    assert agent._last_structured_source == "tool_use_input"


@pytest.mark.asyncio
async def test_get_structured_response_recovers_tool_use_arguments_json(monkeypatch) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    agent.agentscope_agent = object()
    response = DummyResponse(
        [
            {
                "type": "tool_use",
                "name": "generate_response",
                "id": "call_1",
                "input": {"arguments": '{"action": "vote"}'},
            }
        ],
        metadata=None,
    )

    async def fake_serial_call(fn):
        del fn
        return response

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call", fake_serial_call
    )

    decision = await agent.get_structured_response("请输出结构化结果", DummyStructuredDecision)

    assert decision is not None
    assert decision.action == "vote"
    assert agent._last_structured_source == "tool_use_input"


@pytest.mark.asyncio
async def test_get_structured_response_rejects_invalid_tool_use_payload(monkeypatch) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    agent.agentscope_agent = object()
    response = DummyResponse(
        [
            {
                "type": "tool_use",
                "name": "generate_response",
                "id": "call_1",
                "input": {"wrong_field": "vote"},
            }
        ],
        metadata=None,
    )

    async def fake_serial_call(fn):
        del fn
        return response

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call", fake_serial_call
    )

    decision = await agent.get_structured_response("请输出结构化结果", DummyStructuredDecision)

    assert decision is None
    assert agent._last_structured_source == "none"


@pytest.mark.asyncio
async def test_get_structured_response_cleans_interrupt_memory_and_retries(monkeypatch) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    memory = DummyMemory([
        DummyMemoryMsg(
            "bad-tool-result",
            [{"output": "The tool call has been interrupted by the user."}],
        ),
        DummyMemoryMsg("normal", "keep me"),
    ])
    agent.agentscope_agent = SimpleNamespace(memory=memory)
    responses = [
        DummyResponse("I noticed that you have interrupted me. What can I do for you?"),
        DummyResponse(
            [
                {
                    "type": "tool_use",
                    "name": "generate_response",
                    "id": "call_1",
                    "input": {"action": "vote"},
                }
            ],
            metadata=None,
        ),
    ]

    async def fake_serial_call(fn):
        del fn
        return responses.pop(0)

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call",
        fake_serial_call,
    )

    decision = await agent.get_structured_response("请输入结构化结果", DummyStructuredDecision)

    assert decision is not None
    assert decision.action == "vote"
    assert memory.deleted == ["bad-tool-result"]
    assert [msg.id for msg in memory.messages] == ["normal"]


@pytest.mark.asyncio
async def test_get_structured_response_falls_back_to_plain_json_call(monkeypatch) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    agent.agentscope_agent = object()
    responses = [
        DummyResponse("", metadata=None),
        DummyResponse('{"action": "vote"}', metadata=None),
    ]

    async def fake_serial_call(fn):
        del fn
        return responses.pop(0)

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call", fake_serial_call
    )

    decision = await agent.get_structured_response("请输出结构化结果", DummyStructuredDecision)

    assert decision is not None
    assert decision.action == "vote"
    assert agent._last_structured_source == "plain_json"


@pytest.mark.asyncio
async def test_get_structured_response_treats_agentscope_interrupt_as_failure(
    monkeypatch,
) -> None:
    agent = AgentScopeWerewolfAgent(name="P1", role="villager", number=1)
    agent.agentscope_agent = object()
    response = DummyResponse("I noticed that you have interrupted me. What can I do for you?")

    async def fake_serial_call(fn):
        del fn
        return response

    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.agentscope_agent.run_serial_agent_call", fake_serial_call
    )

    decision = await agent.get_structured_response("请输出结构化结果", DummyStructuredDecision)

    assert decision is None
    assert agent._last_structured_source == "interrupted"
