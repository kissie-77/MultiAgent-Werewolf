"""core/action_selector.py 的测试。"""

from unittest.mock import AsyncMock, patch

import pytest

from llm_werewolf.core.action_selector import ActionSelector
from llm_werewolf.core.agent import DemoAgent
from llm_werewolf.core.player import Player
from llm_werewolf.core.roles import Villager


@pytest.fixture
def two_players() -> list[Player]:
    return [
        Player("p1", "Alice", Villager),
        Player("p2", "Bob", Villager),
    ]


def test_build_target_selection_prompt(two_players: list[Player]) -> None:
    prompt = ActionSelector.build_target_selection_prompt(
        role_name="Seer",
        action_description="Check a player",
        possible_targets=two_players,
        allow_skip=True,
        round_number=1,
        phase="night",
    )
    assert "Seer" in prompt
    assert "Alice" in prompt
    assert "跳过" in prompt
    assert "第 1 轮" in prompt


def test_parse_target_selection(two_players: list[Player]) -> None:
    assert ActionSelector.parse_target_selection("2", two_players) == two_players[1]
    assert ActionSelector.parse_target_selection("invalid", two_players) is None
    assert (
        ActionSelector.parse_target_selection("3", two_players, allow_skip=True) is None
    )


def test_parse_yes_no() -> None:
    assert ActionSelector.parse_yes_no("YES") is True
    assert ActionSelector.parse_yes_no("no") is False
    assert ActionSelector.parse_yes_no("是") is True


def test_build_multi_target_prompt(two_players: list[Player]) -> None:
    prompt = ActionSelector.build_multi_target_prompt(
        role_name="Cupid",
        action_description="Link lovers",
        possible_targets=two_players,
        num_targets=2,
    )
    assert "2" in prompt and "不同目标" in prompt


def test_parse_multi_target_selection(two_players: list[Player]) -> None:
    selected = ActionSelector.parse_multi_target_selection("1, 2", two_players, 2)
    assert selected is not None
    assert len(selected) == 2
    assert ActionSelector.parse_multi_target_selection("1, 1", two_players, 2) is None


async def test_get_target_from_agent_uses_agent_response(two_players: list[Player]) -> None:
    agent = DemoAgent(name="Bot", model="demo")

    with patch(
        "llm_werewolf.core.agent.DemoAgent.get_response",
        new_callable=AsyncMock,
        return_value="2",
    ):
        target = await ActionSelector.get_target_from_agent(
            agent,
            role_name="Guard",
            action_description="Protect",
            possible_targets=two_players,
            fallback_random=False,
        )
    assert target == two_players[1]


async def test_get_target_from_agent_random_fallback(two_players: list[Player]) -> None:
    agent = DemoAgent(name="Bot", model="demo")

    with patch(
        "llm_werewolf.core.agent.DemoAgent.get_response",
        new_callable=AsyncMock,
        return_value="not a number",
    ):
        target = await ActionSelector.get_target_from_agent(
            agent,
            role_name="Guard",
            action_description="Protect",
            possible_targets=two_players,
            fallback_random=True,
        )
    assert target in two_players


async def test_ask_yes_no() -> None:
    agent = DemoAgent(name="Bot", model="demo")

    with patch(
        "llm_werewolf.core.agent.DemoAgent.get_response",
        new_callable=AsyncMock,
        return_value="yes",
    ):
        assert await ActionSelector.ask_yes_no(
            agent, context="", question="Save?", role_name="Witch"
        )
