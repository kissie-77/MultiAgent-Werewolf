from __future__ import annotations

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime.roles.villager import Seer
from llm_werewolf.strategy.decisions import (
    SeatChoiceDecision,
    VoteIntentionDecision,
    WitchNightDecision,
)


def _seat_prompt(*seats: int, allow_skip: bool = False) -> str:
    lines = [
        "你是预言家。",
        "任务：选择查验目标",
        "",
        "可选目标：",
    ]
    for seat in seats:
        lines.append(f"- 座位 {seat}：Player{seat}（ID: player_{seat}）")
    if allow_skip:
        lines.append("- 座位 0：跳过（不执行此行动）")
    lines.extend(
        [
            "",
            "请只回复目标玩家的全局座位号，放在 [[数字]] 里。",
            "使用真实座位号，不是列表序号。不要输出其他文字。",
        ]
    )
    return "\n".join(lines)


@pytest.mark.asyncio
async def test_demo_agent_returns_structured_seat_choice() -> None:
    agent = DemoAgent(name="Bot", model="demo", seed=42)
    agent.bind_role(Seer, seat_number=1)

    decision = await agent.get_structured_response(_seat_prompt(2, 3, 4), SeatChoiceDecision)

    assert isinstance(decision, SeatChoiceDecision)
    assert decision.seat == 2


@pytest.mark.asyncio
async def test_demo_agent_returns_structured_witch_decision() -> None:
    agent = DemoAgent(name="Bot", model="demo", seed=42, seat_number=2)

    decision = await agent.get_structured_response(
        "今夜被狼人击杀的是 5 号。WitchNightDecision\n- 座位 4\n- 座位 5",
        WitchNightDecision,
    )

    assert isinstance(decision, WitchNightDecision)
    assert decision.action in {"save", "none", "poison"}


@pytest.mark.asyncio
async def test_demo_agent_returns_structured_vote_intention() -> None:
    agent = DemoAgent(name="Bot", model="demo", seed=42, seat_number=2)

    decision = await agent.get_structured_response(
        "投票意向采集\nVoteIntentionDecision\n- 座位 4\n- 座位 5",
        VoteIntentionDecision,
    )

    assert isinstance(decision, VoteIntentionDecision)
    assert decision.seat in {0, 4, 5}
