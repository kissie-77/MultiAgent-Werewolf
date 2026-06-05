"""End-to-end coverage for AgentScopeWerewolfAgent structured calls."""

from __future__ import annotations

import os
from typing import Any

import pytest
from agentscope.model import ChatResponse

from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent
from llm_werewolf.agent_team.agents.factory import create_react_agent
from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.strategy.contracts.decisions import SeatChoiceDecision, SpeechDecision


class CountingFakeModel:
    """Fake AgentScope model returning OpenAI-style content blocks."""

    def __init__(self, responses: list[list[dict[str, Any]]]) -> None:
        self.stream = False
        self.n_calls = 0
        self._responses = responses

    async def __call__(self, *_args: Any, **_kwargs: Any) -> ChatResponse:
        idx = min(self.n_calls, len(self._responses) - 1)
        self.n_calls += 1
        return ChatResponse(content=list(self._responses[idx]), id=f"resp-{idx}")


def _make_wrapper(responses: list[list[dict[str, Any]]]) -> AgentScopeWerewolfAgent:
    os.environ.setdefault("WW_TEST_KEY", "test-key")
    config = PlayerConfig(
        name="P1",
        model="fake-model",
        base_url="http://localhost:1",
        api_key_env="WW_TEST_KEY",
    )
    backend = create_react_agent(config, agent_name="P1", sys_prompt="You are a player.")
    backend.model = CountingFakeModel(responses)
    return AgentScopeWerewolfAgent(
        name="P1",
        role="villager",
        number=1,
        agentscope_agent=backend,
    )


@pytest.mark.asyncio
async def test_wrapper_recovers_real_react_metadata_from_tool_call() -> None:
    agent = _make_wrapper([
        [
            {
                "type": "tool_use",
                "id": "call_1",
                "name": "generate_response",
                "input": {"seat": 4, "reason": "night target"},
            }
        ]
    ])

    decision = await agent.get_structured_response("choose a target", SeatChoiceDecision)

    assert isinstance(decision, SeatChoiceDecision)
    assert decision.seat == 4
    assert decision.reason == "night target"
    assert agent._last_structured_source == "metadata"
    assert agent.agentscope_agent.model.n_calls == 1


@pytest.mark.asyncio
async def test_wrapper_recovers_real_react_speech_metadata() -> None:
    speech = "我会先听完前置位发言，再结合票型和站边变化判断谁更像狼人。"
    agent = _make_wrapper([
        [
            {
                "type": "tool_use",
                "id": "call_1",
                "name": "generate_response",
                "input": {"public_speech": speech, "private_thought": "keep observing"},
            }
        ]
    ])

    decision = await agent.get_structured_response("make a public speech", SpeechDecision)

    assert isinstance(decision, SpeechDecision)
    assert decision.public_speech == speech
    assert decision.private_thought == "keep observing"
    assert agent._last_structured_source == "metadata"
    assert agent.agentscope_agent.model.n_calls == 1
