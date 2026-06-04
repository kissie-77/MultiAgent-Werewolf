"""引擎缺失的 PHASE_CHANGED 信号测试（警长选举 / 投票 / 结束）。"""

import asyncio
from unittest.mock import MagicMock

from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.types import EventType, GamePhase
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.engine.sheriff_election import SheriffElectionMixin


def _phase_changed_phases(log_event: MagicMock) -> list[str]:
    phases = []
    for call in log_event.call_args_list:
        if call.args and call.args[0] == EventType.PHASE_CHANGED:
            data = call.kwargs.get("data") or {}
            phases.append(data.get("phase"))
    return phases


class _SheriffHarness(SheriffElectionMixin):
    def __init__(self, game_state: GameState, log_event: MagicMock) -> None:
        self.game_state = game_state
        self.locale = Locale("en-US")
        self._log_event = log_event


def test_sheriff_election_emits_phase_changed() -> None:
    log_event = MagicMock()
    state = GameState([Player("v1", "V1", Villager)])
    state.set_phase(GamePhase.SHERIFF_ELECTION)
    state.round_number = 1
    harness = _SheriffHarness(state, log_event)

    asyncio.run(harness.execute_sheriff_election())

    assert GamePhase.SHERIFF_ELECTION.value in _phase_changed_phases(log_event)
