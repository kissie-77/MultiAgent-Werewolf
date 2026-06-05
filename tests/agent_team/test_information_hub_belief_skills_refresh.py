"""InformationHub refreshes belief-matched skills before private LLM decisions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from llm_werewolf.agent_team.communication.information_hub import InformationHub
from llm_werewolf.game_runtime.types import Camp
from llm_werewolf.strategy.voting.intention import VoteIntentionAnchor, VoteIntentionEntry


@dataclass
class FakeRole:
    name: str = "Villager"


@dataclass
class FakePlayer:
    player_id: str
    name: str
    agent: object
    role: object = field(default_factory=FakeRole)

    def is_alive(self) -> bool:
        return True

    def get_role_name(self) -> str:
        return "Villager"

    def get_camp(self) -> Camp:
        return Camp.VILLAGER


class FakeReactAgent:
    async def observe(self, msg) -> None:
        del msg


class FakeAgent:
    model = "demo"

    def get_decision_context(self) -> str:
        return ""

    @property
    def agentscope_agent(self):
        return FakeReactAgent()


class TrackingMemory:
    def __init__(self) -> None:
        self._belief_skill_context = ""

    def add_event(self, event: object) -> None:
        del event

    def get_context_for_decision(self, *, include_belief: bool = True) -> str:
        del include_belief
        return self._belief_skill_context


def test_merge_private_context_refreshes_belief_skills_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    player = FakePlayer(player_id="p1", name="P1", agent=FakeAgent())
    player.agent.memory_manager = TrackingMemory()
    hub = InformationHub()
    hub.set_context_provider(build_observation=lambda _: "obs", get_alive_players=lambda: [player])

    call_order: list[str] = []

    def fake_refresh(actor, *, alive, wolf_camp_mind) -> None:
        del alive, wolf_camp_mind
        call_order.append("refresh")
        actor.agent.memory_manager._belief_skill_context = "【信念匹配的对局经验 · 仅供参考】skill-block"

    monkeypatch.setattr(
        "llm_werewolf.agent_team.communication.information_hub.refresh_player_belief_skills",
        fake_refresh,
    )

    context = hub._merge_private_context(player, "extra")

    assert call_order == ["refresh"]
    assert "skill-block" in context
    assert "extra" in context


def test_collect_vote_intentions_refreshes_each_observer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    players = [
        FakePlayer(player_id="p1", name="P1", agent=FakeAgent()),
        FakePlayer(player_id="p2", name="P2", agent=FakeAgent()),
    ]
    hub = InformationHub()
    hub.set_context_provider(build_observation=lambda _: "", get_alive_players=lambda: players)

    refreshed_ids: list[str] = []

    def fake_refresh(actor, *, alive, wolf_camp_mind) -> None:
        del alive, wolf_camp_mind
        refreshed_ids.append(actor.player_id)

    monkeypatch.setattr(
        "llm_werewolf.agent_team.communication.information_hub.refresh_player_belief_skills",
        fake_refresh,
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
        del (
            agent,
            role_name,
            possible_targets,
            additional_context,
            anchor,
            last_speaker_name,
            round_number,
            phase,
        )
        return VoteIntentionEntry(
            player_id=actor.player_id,
            player_name=actor.name,
            seat=0,
            target_id=None,
            target_name=None,
            reason="watch",
        )

    monkeypatch.setattr(
        "llm_werewolf.agent_team.communication.information_hub.WerewolfAdapterBridge.request_vote_intention",
        fake_request_vote_intention,
    )

    async def _run() -> None:
        await hub._collect_vote_intentions(
            players,
            anchor=VoteIntentionAnchor.INITIAL,
            context_builder=lambda player: f"ctx-{player.player_id}",
            phase="day",
            round_number=1,
        )

    asyncio.run(_run())

    assert refreshed_ids == ["p1", "p2"]
