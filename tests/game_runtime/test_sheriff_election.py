from types import SimpleNamespace

import pytest

from llm_werewolf.game_runtime.engine.sheriff_election import SheriffElectionMixin
from llm_werewolf.game_runtime.i18n.locale import Locale
from llm_werewolf.game_runtime.types import EventType


class _GameState:
    def __init__(self) -> None:
        self.sheriff_election_done = False
        self.sheriff_id: str | None = None

    def set_sheriff(self, player_id: str) -> None:
        self.sheriff_id = player_id


class _SingleCandidateEngine(SheriffElectionMixin):
    def __init__(self) -> None:
        self.game_state = _GameState()
        self.locale = Locale("zh-CN")
        self.events: list[tuple[EventType, str]] = []

    def _log_event(self, event_type: EventType, message: str, **_: object) -> None:
        self.events.append((event_type, message))

    async def _collect_sheriff_candidates(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(player_id="player_1", name="玩家1")]


@pytest.mark.asyncio
async def test_single_sheriff_candidate_logs_no_vote_needed() -> None:
    engine = _SingleCandidateEngine()

    await engine.execute_sheriff_election()

    messages = [message for _, message in engine.events]
    assert "仅有 玩家1 竞选警长，无需投票。" in messages
    assert any(event_type == EventType.SHERIFF_ELECTED for event_type, _ in engine.events)
    assert engine.game_state.sheriff_id == "player_1"
    assert engine.game_state.sheriff_election_done
