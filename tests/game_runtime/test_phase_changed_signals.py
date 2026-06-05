"""引擎缺失的 PHASE_CHANGED 信号测试（警长选举 / 投票 / 结束）。"""

import asyncio
from unittest.mock import MagicMock

from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.types import EventType, GamePhase
from llm_werewolf.game_runtime.i18n.locale import Locale
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


from llm_werewolf.game_runtime.engine.voting_phase import VotingPhaseMixin


class _VotingHarness(VotingPhaseMixin):
    def __init__(self, game_state: GameState, log_event: MagicMock) -> None:
        self.game_state = game_state
        self.locale = Locale("en-US")
        self._log_event = log_event

    async def _handle_knight_duel(self):  # noqa: ANN202
        return []

    async def _handle_death_abilities(self):  # noqa: ANN202
        return []


def test_voting_phase_emits_phase_changed() -> None:
    log_event = MagicMock()
    state = GameState([Player("v1", "V1", Villager), Player("w1", "W1", Werewolf)])
    state.set_phase(GamePhase.DAY_DISCUSSION)
    state.round_number = 1
    harness = _VotingHarness(state, log_event)

    asyncio.run(harness.run_voting_phase())

    assert GamePhase.DAY_VOTING.value in _phase_changed_phases(log_event)


from llm_werewolf.game_runtime.engine.base import GameEngineBase
from llm_werewolf.game_runtime.types import VictoryResult


def test_check_victory_emits_single_ended_phase_changed() -> None:
    captured = []
    engine = GameEngineBase()
    engine.game_state = GameState([Player("v1", "V1", Villager), Player("w1", "W1", Werewolf)])
    engine.game_state.round_number = 1
    engine.on_event = captured.append

    engine.victory_checker = MagicMock()
    engine.victory_checker.check_victory.return_value = VictoryResult(
        has_winner=True, winner_camp="villager", winner_ids=["v1"], reason="all wolves dead"
    )

    assert engine.check_victory() is True

    ended_phase_changes = [
        e
        for e in captured
        if e.event_type == EventType.PHASE_CHANGED
        and (e.data or {}).get("phase") == GamePhase.ENDED.value
    ]
    game_ended = [e for e in captured if e.event_type == EventType.GAME_ENDED]
    assert len(ended_phase_changes) == 1
    assert len(game_ended) == 1
