import asyncio
from dataclasses import dataclass

import pytest

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.game_runtime.events.visibility import VisibilityChannel
from llm_werewolf.game_runtime.types import Camp
from llm_werewolf.strategy.decisions import SpeechDecision
from llm_werewolf.strategy.vote_intention import VoteIntentionEntry, VoteIntentionAnchor
from llm_werewolf.agent_team.communication.information_hub import InformationHub


class FakeAgent:
    name = "fake"
    model = "demo"

    async def get_response(self, message: str) -> str:
        return "[[0]]"

    def add_decision(self, decision: str) -> None:
        return None

    def get_decision_context(self) -> str:
        return ""

    @property
    def agentscope_agent(self):
        return FakeReactAgent()


class FakeReactAgent:
    async def observe(self, msg) -> None:
        del msg


@dataclass
class FakePlayer:
    player_id: str
    name: str
    agent: FakeAgent

    def is_alive(self) -> bool:
        return True

    def get_role_name(self) -> str:
        return "Villager"

    def get_camp(self) -> Camp:
        return Camp.WEREWOLF


def _players(n: int) -> list[FakePlayer]:
    return [
        FakePlayer(player_id=f"p{i}", name=f"P{i}", agent=FakeAgent()) for i in range(1, n + 1)
    ]


@pytest.mark.asyncio
async def test_collect_vote_intentions_is_serial_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hub = InformationHub()
    players = _players(4)
    hub.set_context_provider(
        build_observation=lambda player: f"obs {player.name}", get_alive_players=lambda: players
    )
    active = 0
    max_active = 0

    async def fake_request_vote_intention(
        agent,
        role_name,
        actor,
        possible_targets,
        additional_context,
        *,
        anchor,
        last_speaker_name=None,
        round_number=None,
        phase=None,
    ) -> VoteIntentionEntry:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return VoteIntentionEntry(
            player_id=actor.player_id,
            player_name=actor.name,
            seat=0,
            target_id=None,
            target_name=None,
            reason="test",
        )

    monkeypatch.setattr(
        WerewolfAdapterBridge, "request_vote_intention", staticmethod(fake_request_vote_intention)
    )

    result = await hub._collect_vote_intentions(
        players,
        anchor=VoteIntentionAnchor.INITIAL,
        context_builder=lambda player: f"context {player.name}",
        phase="day_discussion",
        round_number=1,
    )

    assert set(result) == {"p1", "p2", "p3", "p4"}
    assert max_active == 1


@pytest.mark.asyncio
async def test_collect_vote_intentions_respects_configured_parallelism(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hub = InformationHub()
    hub.configure_vote_intention_concurrency(3)
    players = _players(6)
    hub.set_context_provider(
        build_observation=lambda player: f"obs {player.name}", get_alive_players=lambda: players
    )
    active = 0
    max_active = 0

    async def fake_request_vote_intention(
        agent,
        role_name,
        actor,
        possible_targets,
        additional_context,
        *,
        anchor,
        last_speaker_name=None,
        round_number=None,
        phase=None,
    ) -> VoteIntentionEntry:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return VoteIntentionEntry(
            player_id=actor.player_id,
            player_name=actor.name,
            seat=0,
            target_id=None,
            target_name=None,
            reason="test",
        )

    monkeypatch.setattr(
        WerewolfAdapterBridge, "request_vote_intention", staticmethod(fake_request_vote_intention)
    )

    result = await hub._collect_vote_intentions(
        players,
        anchor=VoteIntentionAnchor.AFTER_SPEECH,
        context_builder=lambda player: f"context {player.name}",
        phase="day_discussion",
        round_number=1,
        last_speaker=players[0],
    )

    assert set(result) == {"p1", "p2", "p3", "p4", "p5", "p6"}
    assert max_active == 3


@pytest.mark.asyncio
async def test_collect_vote_intentions_skips_failed_observer(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    hub = InformationHub()
    hub.configure_vote_intention_concurrency(3)
    players = _players(3)
    hub.set_context_provider(
        build_observation=lambda player: f"obs {player.name}", get_alive_players=lambda: players
    )

    async def fake_request_vote_intention(
        agent,
        role_name,
        actor,
        possible_targets,
        additional_context,
        *,
        anchor,
        last_speaker_name=None,
        round_number=None,
        phase=None,
    ) -> VoteIntentionEntry:
        if actor.player_id == "p2":
            raise RuntimeError("intention unavailable")
        return VoteIntentionEntry(
            player_id=actor.player_id,
            player_name=actor.name,
            seat=0,
            target_id=None,
            target_name=None,
            reason="test",
        )

    monkeypatch.setattr(
        WerewolfAdapterBridge, "request_vote_intention", staticmethod(fake_request_vote_intention)
    )

    result = await hub._collect_vote_intentions(
        players,
        anchor=VoteIntentionAnchor.AFTER_SPEECH,
        context_builder=lambda player: f"context {player.name}",
        phase="day_discussion",
        round_number=1,
        last_speaker=players[0],
    )

    assert set(result) == {"p1", "p3"}
    assert "p2" in caplog.text
    assert "P2" in caplog.text
    assert "intention unavailable" in caplog.text


@pytest.mark.asyncio
async def test_roundtable_injects_prior_speeches_into_next_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hub = InformationHub()
    players = _players(2)
    hub.set_context_provider(
        build_observation=lambda player: f"obs {player.name}", get_alive_players=lambda: players
    )
    seen_contexts: list[str] = []

    async def fake_request_speech(agent, context, instruction="", *, roundtable_phase=None):
        del agent, instruction, roundtable_phase
        seen_contexts.append(context)
        if len(seen_contexts) == 1:
            return SpeechDecision(public_speech="我建议今晚刀4号，先压掉可能的带队位。")
        return SpeechDecision(public_speech="我同意上一位先刀4号，因为这个位置后续可能带队。")

    monkeypatch.setattr(
        WerewolfAdapterBridge, "request_speech", staticmethod(fake_request_speech)
    )

    await hub.run_roundtable(
        players,
        channel=VisibilityChannel.WOLF_TEAM,
        context_builder=lambda player: f"context {player.name}",
        instruction="",
        phase="night",
        round_number=1,
        audience=players,
    )

    assert len(seen_contexts) == 2
    assert "【本轮已听到的发言】" not in seen_contexts[0]
    assert "【本轮已听到的发言】" in seen_contexts[1]
    assert "P1: 我建议今晚刀4号" in seen_contexts[1]
    assert "不要像没有听到前面发言一样重新自说自话" in seen_contexts[1]
