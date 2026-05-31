"""Bridge mind-state integration tests."""

from __future__ import annotations

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.game_runtime.roles.werewolf import Werewolf
from llm_werewolf.strategy.vote_intention import VoteIntentionAnchor


class _Target:
    def __init__(self, player_id: str, name: str, seat: int) -> None:
        self.player_id = player_id
        self.name = name
        self._seat = seat

    def is_alive(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_request_mind_state_with_demo_agent() -> None:
    agent = DemoAgent(name="demo", model="demo", seat_number=1, seed=7)
    agent.bind_role(Villager, seat_number=1)
    actor = type(
        "Actor",
        (),
        {
            "player_id": "player_1",
            "name": "P1",
            "agent": agent,
            "get_role_name": lambda self: "Villager",
        },
    )()
    targets = [_Target("player_2", "P2", 2), _Target("player_3", "P3", 3)]
    entry, mind = await WerewolfAdapterBridge.request_mind_state(
        agent,
        "Villager",
        actor,
        targets,
        "上下文",
        anchor=VoteIntentionAnchor.INITIAL,
        round_number=1,
        phase="Day",
    )
    assert entry.seat >= 0
    assert mind.first_order


@pytest.mark.asyncio
async def test_demo_wolf_emits_wolf_camp_delta() -> None:
    agent = DemoAgent(name="wolf", model="demo", seat_number=3, seed=3)
    agent.bind_role(Werewolf, seat_number=3)
    from llm_werewolf.agent_team.agents.demo_policy import build_mind_state

    decision = build_mind_state(
        "- 座位 1：A\n- 座位 2：B",
        seat_number=3,
        rng=agent._rng(),
        random_mode=False,
        is_wolf=True,
    )
    assert decision.wolf_camp_delta is not None
    assert decision.wolf_camp_delta.god_role_intel
