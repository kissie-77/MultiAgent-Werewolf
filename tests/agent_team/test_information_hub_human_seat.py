"""InformationHub human-seat handling (BUG-3).

A browser-human seat must be treated like the stdin human: skipped by the
AI-only vote-intention machinery and exempt from the per-step LLM timeout, so
its only clock is the HumanInputBroker deadline.
"""

import asyncio

import pytest

from llm_werewolf.agent_team.communication.information_hub import InformationHub


class _Agent:
    def __init__(self, model: str) -> None:
        self.model = model


class _Player:
    def __init__(self, model: str) -> None:
        self.agent = _Agent(model)


def test_is_human_player_recognizes_web_human() -> None:
    assert InformationHub._is_human_player(_Player("web-human")) is True
    assert InformationHub._is_human_player(_Player("human")) is True
    assert InformationHub._is_human_player(_Player("deepseek-chat")) is False


async def _slow() -> str:
    await asyncio.sleep(0.2)
    return "speech"


async def test_await_step_skips_timeout_when_flagged() -> None:
    hub = InformationHub()
    hub._day_step_timeout = 0.05
    assert await hub._await_step(_slow(), "day_discussion", skip=True) == "speech"


async def test_await_step_still_times_out_without_skip() -> None:
    hub = InformationHub()
    hub._day_step_timeout = 0.05
    with pytest.raises(asyncio.TimeoutError):
        await hub._await_step(_slow(), "day_discussion")
