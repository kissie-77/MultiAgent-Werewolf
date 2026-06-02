"""Night prompt context regression tests."""

from __future__ import annotations

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime.registries.role_night_plans import (
    plan_guard_protect,
    plan_seer_check,
    plan_witch_actions,
)
from llm_werewolf.game_runtime.actions.villager import WitchPoisonAction
from llm_werewolf.game_runtime.roles import Guard, Seer, Witch, Villager, Werewolf
from llm_werewolf.game_runtime.roles.werewolf import build_werewolf_team_context
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.strategy.decisions import WitchNightDecision


class _CaptureInteraction:
    def __init__(self) -> None:
        self.additional_context = ""

    async def request_seat_choice(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.additional_context = kwargs.get("additional_context", "")
        return None


class _WitchPoisonInteraction:
    async def request_witch_night_choice(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return WitchNightDecision(action="poison", seat=3, reason="test poison")


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


@pytest.mark.asyncio
async def test_witch_poison_action_carries_current_decision_metadata() -> None:
    witch = Player("player_1", "Witch1", Witch, agent=DemoAgent(name="Witch1", model="demo"))
    old_target = Player(
        "player_2", "Villager2", Villager, agent=DemoAgent(name="Villager2", model="demo")
    )
    poison_target = Player(
        "player_3", "Villager3", Villager, agent=DemoAgent(name="Villager3", model="demo")
    )
    state = GameState([witch, old_target, poison_target])
    witch.role.has_save_potion = False
    interaction = _WitchPoisonInteraction()

    actions = await plan_witch_actions(witch.role, state, interaction)

    assert len(actions) == 1
    assert isinstance(actions[0], WitchPoisonAction)
    metadata = getattr(actions[0], "_decision_metadata")
    assert metadata["decision_seat"] == 3
    assert metadata["resolved_target_id"] == "player_3"
    assert metadata["structured_decision"]["action"] == "poison"
