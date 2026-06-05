from __future__ import annotations

import pytest

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.strategy.belief.state import BeliefState
from llm_werewolf.strategy.voting.intention import VoteIntentionAnchor


class _StubAgent:
    def __init__(self, response: str) -> None:
        self._response = response
        self.belief_state = BeliefState(observer_seat=1, last_vote_seat=2)

    async def get_response(self, prompt: str) -> str:
        return self._response

    def get_structured_response(self, message: str, structured_model: type):
        return None


class _StubPlayer:
    def __init__(self, player_id: str, name: str, seat: int, role_name: str, agent: object) -> None:
        self.player_id = player_id
        self.name = name
        self.seat_number = seat
        self._role_name = role_name
        self.agent = agent

    def get_role_name(self) -> str:
        return self._role_name


@pytest.mark.asyncio
async def test_request_mind_state_fallback_sets_reason_for_vote_change() -> None:
    agent = _StubAgent("[[3]]")
    actor = _StubPlayer("player_1", "玩家1", 1, "Villager", agent)
    targets = [
        _StubPlayer("player_2", "玩家2", 2, "Villager", None),
        _StubPlayer("player_3", "玩家3", 3, "Villager", None),
    ]

    entry, mind = await WerewolfAdapterBridge.request_mind_state(
        agent,
        role_name="Villager",
        actor=actor,
        possible_targets=targets,
        additional_context="测试上下文",
        anchor=VoteIntentionAnchor.AFTER_SPEECH,
        last_speaker_name="玩家9",
        round_number=1,
        phase="day_discussion",
    )

    assert entry.seat == 3
    assert entry.reason == "[[3]]"
    assert mind.vote_seat == 3
    assert mind.vote_reason == "[[3]]"


@pytest.mark.asyncio
async def test_request_mind_state_fallback_synthesizes_reason_for_blank_response() -> None:
    agent = _StubAgent("")
    actor = _StubPlayer("player_1", "玩家1", 1, "Villager", agent)
    targets = [
        _StubPlayer("player_2", "玩家2", 2, "Villager", None),
    ]

    entry, mind = await WerewolfAdapterBridge.request_mind_state(
        agent,
        role_name="Villager",
        actor=actor,
        possible_targets=targets,
        additional_context="测试上下文",
        anchor=VoteIntentionAnchor.AFTER_SPEECH,
        last_speaker_name="玩家9",
        round_number=1,
        phase="day_discussion",
    )

    assert entry.seat == 0
    assert entry.reason == "fallback seat=0"
    assert mind.vote_seat == 0
    assert mind.vote_reason == "fallback seat=0"
