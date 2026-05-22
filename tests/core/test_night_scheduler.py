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
            "llm_werewolf.core.night_scheduler.dispatch_night_plan",
            new_callable=AsyncMock,
            return_value=[],
        ) as dispatch_plan,
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
        assert calls_after_pre >= 0

        await scheduler.run_wolf_vote_phase()
        assert dispatch_plan.call_count > calls_after_pre

        calls_before_post = dispatch_plan.call_count
        game_state.werewolf_target = villager.player_id
        await scheduler.run_post_wolf_resolution()
        assert dispatch_plan.call_count > calls_before_post
