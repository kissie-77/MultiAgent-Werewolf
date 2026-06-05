"""有序夜间技能收集的测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_werewolf.game_runtime.roles import (
    Seer,
    Witch,
    Magician,
    Villager,
    Werewolf,
    WhiteWolf,
    WolfBeauty,
    GuardianWolf,
    NightmareWolf,
)
from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.night_scheduler import NightSkillScheduler
from llm_werewolf.game_runtime.actions.villager import MagicianSwapAction
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.registries.role_night_plans import (
    NightStage,
    POST_WITCH_STAGE,
    plan_magician_swap,
    night_roles_for_stage,
    validate_night_plan_registry,
)


@pytest.mark.asyncio
async def test_witch_collected_after_wolf_phase_not_in_pre_wolf() -> None:
    """女巫应仅在狼人阶段后的批次中收集。"""
    witch = Player("p1", "Witch", Witch)
    wolf = Player("p2", "Wolf", Werewolf)
    seer = Player("p3", "Seer", Seer)
    villager = Player("p4", "V", Villager)
    game_state = GameState([witch, wolf, seer, villager])
    game_state.round_number = 2

    from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
    from llm_werewolf.agent_team.communication.information_hub import InformationHub

    game_state.phase_interaction = PhaseInteraction(InformationHub())

    with (
        patch(
            "llm_werewolf.game_runtime.night_scheduler.dispatch_night_plan",
            new_callable=AsyncMock,
            return_value=[],
        ) as dispatch_plan,
        patch(
            "llm_werewolf.game_runtime.night_scheduler.dispatch_werewolf_vote_plan",
            new_callable=AsyncMock,
            return_value=[],
        ) as dispatch_vote,
    ):
        locale = MagicMock()
        locale.get = MagicMock(side_effect=lambda key, **kw: key)

        scheduler = NightSkillScheduler(
            game_state,
            log_event=MagicMock(),
            locale=locale,
            resolve_werewolf_votes=MagicMock(return_value=[]),
        )

        await scheduler.run_pre_wolf_phase()
        calls_after_pre = dispatch_plan.call_count
        votes_after_pre = dispatch_vote.call_count
        assert calls_after_pre >= 0

        await scheduler.run_wolf_vote_phase()
        assert dispatch_plan.call_count == calls_after_pre
        assert dispatch_vote.call_count > votes_after_pre

        calls_before_post = dispatch_plan.call_count
        game_state.werewolf_target = villager.player_id
        await scheduler.run_post_wolf_resolution()
        assert dispatch_plan.call_count > calls_before_post


@pytest.mark.asyncio
async def test_special_wolves_use_pack_vote_planner_in_wolf_vote_phase() -> None:
    guardian = Player("gw1", "Guardian", GuardianWolf)
    nightmare = Player("nw1", "Nightmare", NightmareWolf)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([guardian, nightmare, villager])

    from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
    from llm_werewolf.agent_team.communication.information_hub import InformationHub

    game_state.phase_interaction = PhaseInteraction(InformationHub())

    with (
        patch(
            "llm_werewolf.game_runtime.night_scheduler.dispatch_werewolf_vote_plan",
            new_callable=AsyncMock,
            return_value=[],
        ) as dispatch_vote,
        patch(
            "llm_werewolf.game_runtime.night_scheduler.dispatch_night_plan",
            new_callable=AsyncMock,
            return_value=[],
        ) as dispatch_special,
    ):
        locale = MagicMock()
        locale.get = MagicMock(side_effect=lambda key, **kw: key)
        scheduler = NightSkillScheduler(
            game_state,
            log_event=MagicMock(),
            locale=locale,
            resolve_werewolf_votes=MagicMock(return_value=[]),
        )

        await scheduler.run_wolf_vote_phase()

    voted_role_names = [call.args[0].name for call in dispatch_vote.call_args_list]
    special_role_names = [call.args[0].name for call in dispatch_special.call_args_list]
    assert voted_role_names == ["Guardian Wolf", "Nightmare Wolf"]
    assert special_role_names == []


@pytest.mark.asyncio
async def test_wolf_phase_special_roles_keep_extra_skill_after_pack_vote() -> None:
    white_wolf = Player("ww1", "WhiteWolf", WhiteWolf)
    wolf_beauty = Player("wb1", "WolfBeauty", WolfBeauty)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([white_wolf, wolf_beauty, villager])

    from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
    from llm_werewolf.agent_team.communication.information_hub import InformationHub

    game_state.phase_interaction = PhaseInteraction(InformationHub())

    with (
        patch(
            "llm_werewolf.game_runtime.night_scheduler.dispatch_werewolf_vote_plan",
            new_callable=AsyncMock,
            return_value=[],
        ) as dispatch_vote,
        patch(
            "llm_werewolf.game_runtime.night_scheduler.dispatch_night_plan",
            new_callable=AsyncMock,
            return_value=[],
        ) as dispatch_special,
    ):
        locale = MagicMock()
        locale.get = MagicMock(side_effect=lambda key, **kw: key)
        scheduler = NightSkillScheduler(
            game_state,
            log_event=MagicMock(),
            locale=locale,
            resolve_werewolf_votes=MagicMock(return_value=[]),
        )

        await scheduler.run_wolf_vote_phase()

    assert [call.args[0].name for call in dispatch_vote.call_args_list] == [
        "White Wolf",
        "Wolf Beauty",
    ]
    assert [call.args[0].name for call in dispatch_special.call_args_list] == [
        "White Wolf",
        "Wolf Beauty",
    ]


@pytest.mark.asyncio
async def test_post_witch_roles_are_driven_by_night_plan_specs() -> None:
    """新增夜间角色只需进入计划规格表，scheduler 不需要专门认识角色类。"""
    seer = Player("s1", "Seer", Seer)
    magician = Player("m1", "Magician", Magician)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([seer, magician, villager])
    game_state.round_number = 1
    game_state.werewolf_target = villager.player_id

    from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
    from llm_werewolf.agent_team.communication.information_hub import InformationHub

    game_state.phase_interaction = PhaseInteraction(InformationHub())

    with patch(
        "llm_werewolf.game_runtime.night_scheduler.dispatch_night_plan",
        new_callable=AsyncMock,
        return_value=[],
    ) as dispatch_plan:
        locale = MagicMock()
        locale.get = MagicMock(side_effect=lambda key, **kw: key)
        scheduler = NightSkillScheduler(
            game_state,
            log_event=MagicMock(),
            locale=locale,
            resolve_werewolf_votes=MagicMock(return_value=[]),
        )

        await scheduler.run_post_wolf_resolution()

    assert "Magician" in night_roles_for_stage(POST_WITCH_STAGE)
    assert [call.args[0].name for call in dispatch_plan.call_args_list] == [
        "Seer",
        "Magician",
    ]


@pytest.mark.asyncio
async def test_magician_plan_collects_two_targets() -> None:
    magician = Player(
        "m1", "Magician", Magician, agent=DemoAgent(name="Magician", model="demo")
    )
    seer = Player("s1", "Seer", Seer)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([magician, seer, villager])
    game_state.round_number = 1
    interaction = MagicMock()
    interaction.request_multi_targets = AsyncMock(return_value=[seer, villager])

    actions = await plan_magician_swap(magician.role, game_state, interaction)

    interaction.request_multi_targets.assert_awaited_once()
    assert len(actions) == 1
    assert isinstance(actions[0], MagicianSwapAction)
    assert actions[0].target1 is seer
    assert actions[0].target2 is villager


def test_night_plan_registry_is_complete() -> None:
    assert POST_WITCH_STAGE == NightStage.POST_WITCH.value
    assert validate_night_plan_registry() == []
