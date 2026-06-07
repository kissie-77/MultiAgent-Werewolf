"""PhaseInteraction timeout routing tests."""

import asyncio

import pytest

from llm_werewolf.game_runtime.interaction.phase_interaction import PhaseInteraction


class _Hub:
    pass


class _Agent:
    def __init__(self, model: str) -> None:
        self.model = model


async def _slow() -> str:
    await asyncio.sleep(0.2)
    return "done"


async def test_web_human_seat_skips_phase_timeout() -> None:
    # BUG-3: a browser-human seat must NOT be hard-cancelled by the LLM phase
    # timeout (45s); the HumanInputBroker owns the human deadline + graceful
    # fallback instead. With a tiny phase budget the human coro still completes.
    interaction = PhaseInteraction(_Hub())
    interaction._night_timeout = 0.05
    assert await interaction._await_with_timeout(_slow(), "night", agent=_Agent("web-human")) == "done"


async def test_stdin_human_seat_skips_phase_timeout() -> None:
    interaction = PhaseInteraction(_Hub())
    interaction._night_timeout = 0.05
    assert await interaction._await_with_timeout(_slow(), "night", agent=_Agent("human")) == "done"


async def test_ai_agent_still_times_out() -> None:
    interaction = PhaseInteraction(_Hub())
    interaction._night_timeout = 0.05
    with pytest.raises(asyncio.TimeoutError):
        await interaction._await_with_timeout(_slow(), "night", agent=_Agent("deepseek-chat"))


async def test_no_agent_preserves_existing_timeout_behavior() -> None:
    # Back-compat: when no agent is supplied (all current AI flows), behavior is
    # unchanged — the phase timeout still fires.
    interaction = PhaseInteraction(_Hub())
    interaction._night_timeout = 0.05
    with pytest.raises(asyncio.TimeoutError):
        await interaction._await_with_timeout(_slow(), "night")


def test_timeout_for_phase_uses_day_budget_for_day_discussion() -> None:
    interaction = PhaseInteraction(_Hub())
    interaction.configure_timeouts(night_timeout=45, day_timeout=180, vote_timeout=60)
    assert interaction._timeout_for_phase("day_discussion") == 180.0
    assert interaction._timeout_for_phase("sheriff_election") == 180.0
    assert interaction._timeout_for_phase("day_voting") == 60.0
    assert interaction._timeout_for_phase("Night") == 45.0


def test_timeout_for_phase_legacy_labels_still_work() -> None:
    interaction = PhaseInteraction(_Hub())
    interaction.configure_timeouts(night_timeout=30, day_timeout=300, vote_timeout=45)
    assert interaction._timeout_for_phase("Discussion") == 300.0
    assert interaction._timeout_for_phase("Voting") == 45.0
