from __future__ import annotations

import pytest

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge


class _StubSpeechAgent:
    def __init__(self) -> None:
        self.structured_calls = 0
        self.text_calls = 0
        self.agentscope_agent = object()

    async def get_structured_response(self, message: str, structured_model: type):
        self.structured_calls += 1
        return None

    async def get_response(self, message: str) -> str:
        self.text_calls += 1
        return "[[我认为这轮应该继续听发言，再结合票型判断身份。]]"


@pytest.mark.asyncio
async def test_request_speech_falls_back_after_single_structured_attempt() -> None:
    agent = _StubSpeechAgent()

    decision = await WerewolfAdapterBridge.request_speech(
        agent,
        context="测试发言上下文",
        instruction="请发言",
    )

    assert agent.structured_calls == 1
    assert agent.text_calls == 1
    assert "继续听发言" in decision.public_speech
