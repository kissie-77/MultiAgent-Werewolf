"""Tests for ordered night skill collection."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_werewolf.core.game_state import GameState
from llm_werewolf.core.night_scheduler import NightSkillScheduler
from llm_werewolf.core.player import Player
from llm_werewolf.core.roles import Seer, Villager, Werewolf, Witch


@pytest.mark.asyncio
async def test_witch_collected_after_wolf_phase_not_in_pre_wolf() -> None:
    """Witch should only be gathered in post-wolf batch."""
    witch = Player("p1", "Witch", Witch)
    wolf = Player("p2", "Wolf", Werewolf)
    seer = Player("p3", "Seer", Seer)
    villager = Player("p4", "V", Villager)
    game_state = GameState([witch, wolf, seer, villager])
    game_state.round_number = 2

    from llm_werewolf.adapter.information_hub import InformationHub
    from llm_werewolf.core.phase_interaction import PhaseInteraction

    game_state.phase_interaction = PhaseInteraction(InformationHub())

    with (
        patch(
            "llm_werewolf.core.night_scheduler.plan_werewolf_vote",
            new_callable=AsyncMock,
            return_value=[],
        ) as wolf_plan,
        patch(
            "llm_werewolf.core.night_scheduler.plan_witch_actions",
            new_callable=AsyncMock,
            return_value=[],
        ) as witch_plan,
        patch(
            "llm_werewolf.core.night_scheduler.plan_seer_check",
            new_callable=AsyncMock,
            return_value=[],
        ) as seer_plan,
    ):
        locale = MagicMock()
        locale.get = MagicMock(side_effect=lambda key, **kw: key)

        scheduler = NightSkillScheduler(
            game_state,
            log_event=MagicMock(),
            locale=locale,
            resolve_werewolf_votes=MagicMock(return_value=[]),
        )

        await scheduler.run()
        witch_plan.assert_not_called()
        wolf_plan.assert_called_once()

        await scheduler.run_post_wolf_resolution()
        witch_plan.assert_called_once()
        seer_plan.assert_called_once()
        assert wolf_plan.call_count == 1
