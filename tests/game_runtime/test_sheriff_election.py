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


class _TimeoutCampaignEngine(SheriffElectionMixin):
    """2+ candidates, but campaign speeches blow up (e.g. LLM timeout)."""

    def __init__(self) -> None:
        self.game_state = _GameState()
        self.locale = Locale("zh-CN")
        self.events: list[tuple[EventType, str]] = []

    def _log_event(self, event_type: EventType, message: str, **_: object) -> None:
        self.events.append((event_type, message))

    async def _collect_sheriff_candidates(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(player_id="player_1", name="玩家1"),
            SimpleNamespace(player_id="player_2", name="玩家2"),
        ]

    async def _conduct_campaign_speeches(self, _candidates: object) -> None:
        raise TimeoutError("llm timed out")


@pytest.mark.asyncio
async def test_sheriff_campaign_failure_does_not_abort_game() -> None:
    """A phase-level failure during sheriff election must NOT propagate.

    Otherwise play_game() dies (status=failed) with no further events and the
    SSE frontend freezes on the “警长竞选” screen, unable to advance.
    """
    engine = _TimeoutCampaignEngine()

    # Must not raise.
    await engine.execute_sheriff_election()

    # Election abandoned, but the phase can still advance to day.
    assert engine.game_state.sheriff_election_done
    assert engine.game_state.sheriff_id is None
    assert any(event_type == EventType.ERROR for event_type, _ in engine.events)
