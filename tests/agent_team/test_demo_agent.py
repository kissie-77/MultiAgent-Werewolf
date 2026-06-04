"""DemoAgent offline policy and bridge integration tests."""

from __future__ import annotations

from random import Random
from types import SimpleNamespace

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.agent_team.agents.demo_policy import (
    DemoPromptKind,
    classify_prompt,
    build_speech,
    respond,
)
from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.game_runtime.roles.villager import Seer, Villager
from llm_werewolf.strategy.decisions import (
    SeatChoiceDecision,
    VoteIntentionDecision,
    WitchNightDecision,
    is_valid_public_speech,
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
    lines.extend([
        "",
        "请只回复目标玩家的全局座位号，放在 [[数字]] 中。",
        "使用真实座位号，不是列表序号。不要输出其他文字。",
    ])
    return "\n".join(lines)


def test_classify_prompt_variants() -> None:
    assert classify_prompt("请只回复 [[1]] 表示是，[[0]] 表示否。") == DemoPromptKind.YES_NO
    assert classify_prompt("投票意向采集\nVoteIntentionDecision") == DemoPromptKind.VOTE_INTENTION
    assert classify_prompt("请在本回合三选一：救人(save) / 毒人(poison) / 不行动(none)。") == DemoPromptKind.WITCH
    assert classify_prompt("请在本回合二选一：毒人(poison) / 不行动(none)。") == DemoPromptKind.WITCH
    assert classify_prompt("请选择 2 个不同目标。\nMultiSeatChoiceDecision") == DemoPromptKind.MULTI_SEAT
    assert classify_prompt(_seat_prompt(2, 3)) == DemoPromptKind.SEAT_CHOICE
    assert classify_prompt("请发表你的公开发言。") == DemoPromptKind.SPEECH


def test_respond_seat_choice_is_deterministic() -> None:
    prompt = _seat_prompt(2, 3, 4)
    rng = Random(7)
    first = respond(prompt, seat_number=1, rng=rng, random_mode=False)
    second = respond(prompt, seat_number=1, rng=Random(7), random_mode=False)
    assert first == second == "[[2]]"
    assert respond(prompt, seat_number=2, rng=Random(7), random_mode=False) == "[[3]]"


def test_respond_yes_no_and_vote_intention() -> None:
    yes_no = respond(
        "请只回复 [[1]] 表示是，[[0]] 表示否。",
        seat_number=3,
        rng=Random(1),
        random_mode=False,
    )
    assert yes_no == "[[1]]"

    vote_prompt = "\n".join([
        "投票意向采集",
        "VoteIntentionDecision",
        "可选目标：",
        "- 座位 4：A（ID: player_4）",
        "- 座位 5：B（ID: player_5）",
    ])
    vote = respond(
        vote_prompt,
        seat_number=2,
        rng=Random(1),
        random_mode=False,
    )
    assert vote == "[[5]]"


@pytest.mark.asyncio
async def test_demo_agent_get_response_matches_bridge_parsers() -> None:
    agent = DemoAgent(name="Bot", model="demo", seed=42)
    agent.bind_role(Seer, seat_number=1)

    seat_prompt = _seat_prompt(2, 3)
    seat_response = await agent.get_response(seat_prompt)
    targets = [
        SimpleNamespace(player_id="player_2", name="P2"),
        SimpleNamespace(player_id="player_3", name="P3"),
    ]
    picked = WerewolfAdapterBridge.parse_target_selection(seat_response, targets, allow_skip=False)
    assert picked is not None
    assert WerewolfAdapterBridge.get_player_seat(picked) == 2

    yes_no_prompt = WerewolfAdapterBridge.build_yes_no_prompt("预言家", "是否上警？")
    yes_no_response = await agent.get_response(yes_no_prompt)
    assert WerewolfAdapterBridge.parse_yes_no(yes_no_response) is True

    speech_response = await agent.get_response("请结合当前局势发表公开发言。")
    decision = WerewolfAdapterBridge.parse_speech(speech_response)
    assert is_valid_public_speech(decision.public_speech)


@pytest.mark.asyncio
async def test_demo_agent_is_reproducible_with_seed() -> None:
    async def run_once(seed: int) -> list[str]:
        agent = DemoAgent(name="Bot", model="demo", seed=seed, seat_number=3)
        prompts = [
            _seat_prompt(1, 2, 3, 4),
            "请只回复 [[1]] 表示是，[[0]] 表示否。",
            "请结合当前局势发表公开发言。",
        ]
        return [await agent.get_response(prompt) for prompt in prompts]

    assert await run_once(99) == await run_once(99)

    seat_prompt = _seat_prompt(1, 2, 3, 4)
    seat_one = DemoAgent(name="Bot", model="demo", seed=99, seat_number=1)
    seat_two = DemoAgent(name="Bot", model="demo", seed=99, seat_number=2)
    assert await seat_one.get_response(seat_prompt) != await seat_two.get_response(seat_prompt)


def test_demo_agent_fallback_speech_is_valid() -> None:
    agent = DemoAgent(name="Bot", model="demo", seat_number=2)
    agent.bind_role(Villager, seat_number=2)
    fallback = agent._generate_fallback_response("bad", "too short")
    decision = WerewolfAdapterBridge.parse_speech(fallback)
    assert is_valid_public_speech(decision.public_speech)


def test_demo_speech_does_not_reveal_role() -> None:
    speech = build_speech(seat_number=4, role_display="狼人")

    assert "狼人" not in speech
    assert "我是 4 号位" in speech


def test_demo_agent_tracks_decision_context() -> None:
    agent = DemoAgent(name="Bot", model="demo", seat_number=1)
    agent.add_decision("[[2]]")
    agent.add_decision("[[1]]")
    context = agent.get_decision_context()
    assert "最近离线决策摘要" in context
    assert "[[2]]" in context
