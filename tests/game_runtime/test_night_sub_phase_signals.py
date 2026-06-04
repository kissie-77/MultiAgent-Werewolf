"""NightSkillScheduler 与狼队夜聊的 SUB_PHASE 信号测试。"""

import asyncio
from unittest.mock import MagicMock

from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.night_scheduler import NightSkillScheduler


def _sub_phase_names(log_event: MagicMock) -> list[str]:
    names = []
    for call in log_event.call_args_list:
        if call.args and call.args[0] == EventType.SUB_PHASE:
            names.append(call.kwargs["data"]["name"])
    return names


def _scheduler(log_event: MagicMock) -> NightSkillScheduler:
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    state = GameState([wolf, villager])
    state.round_number = 1
    return NightSkillScheduler(
        state,
        log_event=log_event,
        locale=MagicMock(),
        resolve_werewolf_votes=lambda: [],
    )


def test_run_pre_wolf_phase_emits_pre_wolf_sub_phase() -> None:
    log_event = MagicMock()
    scheduler = _scheduler(log_event)
    asyncio.run(scheduler.run_pre_wolf_phase())
    assert "pre_wolf" in _sub_phase_names(log_event)


def test_run_wolf_vote_phase_emits_werewolf_kill_sub_phase() -> None:
    log_event = MagicMock()
    scheduler = _scheduler(log_event)
    asyncio.run(scheduler.run_wolf_vote_phase())
    assert "werewolf_kill" in _sub_phase_names(log_event)


def test_run_post_wolf_resolution_emits_witch_then_seer_sub_phases() -> None:
    log_event = MagicMock()
    scheduler = _scheduler(log_event)
    asyncio.run(scheduler.run_post_wolf_resolution())
    names = _sub_phase_names(log_event)
    assert "witch_decide" in names
    assert "seer_check" in names
