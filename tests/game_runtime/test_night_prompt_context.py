"""Night prompt context regression tests."""

from __future__ import annotations

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime.registries.role_night_plans import (
    plan_guard_protect,
    plan_seer_check,
)
from llm_werewolf.game_runtime.roles import Guard, Seer, Villager, Werewolf
from llm_werewolf.game_runtime.roles.werewolf import build_werewolf_team_context
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.player import Player


class _CaptureInteraction:
    def __init__(self) -> None:
        self.additional_context = ""

    async def request_seat_choice(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.additional_context = kwargs.get("additional_context", "")
        return None


def test_werewolf_team_context_does_not_repeat_role_private_notes() -> None:
    wolf = Player("w1", "Wolf1", Werewolf, agent=DemoAgent(name="Wolf1", model="demo"))
    teammate = Player("w2", "Wolf2", Werewolf, agent=DemoAgent(name="Wolf2", model="demo"))
    villager = Player("v1", "Villager1", Villager, agent=DemoAgent(name="Villager1", model="demo"))
    state = GameState([wolf, teammate, villager])

    context = build_werewolf_team_context(wolf.role, state, ["Wolf1", "Wolf2"])

    assert "你的身份是" not in context
    assert "【身份提示】" not in context
    assert "存活的狼队友" not in context
    assert "所有狼人将在今晚投票决定击杀目标" in context


@pytest.mark.asyncio
async def test_guard_night_context_only_includes_extra_restrictions() -> None:
    guard = Player("g1", "Guard1", Guard, agent=DemoAgent(name="Guard1", model="demo"))
    target = Player("v1", "Villager1", Villager, agent=DemoAgent(name="Villager1", model="demo"))
    state = GameState([guard, target])
    guard.role.last_protected = target.player_id
    interaction = _CaptureInteraction()

    await plan_guard_protect(guard.role, state, interaction)

    assert "守卫请睁眼" not in interaction.additional_context
    assert "不能连续两晚守护" in interaction.additional_context


@pytest.mark.asyncio
async def test_seer_night_context_only_includes_checked_history() -> None:
    seer = Player("s1", "Seer1", Seer, agent=DemoAgent(name="Seer1", model="demo"))
    target = Player("v1", "Villager1", Villager, agent=DemoAgent(name="Villager1", model="demo"))
    state = GameState([seer, target])
    state.seer_checked[1] = target.player_id
    interaction = _CaptureInteraction()

    await plan_seer_check(seer.role, state, interaction)

    assert "预言家请睁眼" not in interaction.additional_context
    assert "已查验" in interaction.additional_context
