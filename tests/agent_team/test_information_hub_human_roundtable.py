from unittest.mock import AsyncMock

from llm_werewolf.agent_team.base import DemoAgent, HumanAgent
from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.agent_team.information_hub import InformationHub
from llm_werewolf.agent_team.visibility import VisibilityChannel
from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.strategy.decisions import SpeechDecision
from llm_werewolf.strategy.vote_intention import (
    VoteIntentionAnchor,
    VoteIntentionEntry,
)


class FakeSpeechProvider:
    async def speak(self, **_kwargs):
        return SpeechDecision.model_construct(
            public_speech="我是人类玩家的公开发言",
            private_thought=None,
        )


class CapturingSpeechProvider:
    def __init__(self, decisions: list[SpeechDecision]) -> None:
        self.decisions = decisions
        self.contexts: list[str] = []

    async def speak(self, **kwargs):
        self.contexts.append(kwargs["context"])
        return self.decisions.pop(0)


def _human_player(player_id: str = "player_1", name: str = "Human") -> Player:
    agent = HumanAgent(name=name, model="human")
    return Player(player_id, name, Villager, agent=agent, ai_model="human")


def _demo_player(player_id: str = "player_2", name: str = "Bot") -> Player:
    agent = DemoAgent(name=name)
    return Player(player_id, name, Villager, agent=agent, ai_model="demo")


async def test_roundtable_calls_human_speaker_even_without_react_agents() -> None:
    player = _human_player()
    hub = InformationHub()
    hub.set_context_provider(
        build_observation=lambda _player: "filtered observation",
        get_alive_players=lambda: [player],
    )
    speeches = []

    routed = await hub.run_roundtable(
        [player],
        channel=VisibilityChannel.PUBLIC,
        context_builder=lambda _speaker: "context",
        instruction="请发言",
        phase="day_discussion",
        round_number=1,
        on_speech=lambda speaker, decision, route: speeches.append(
            (speaker, decision.public_speech, route)
        ),
        human_input_provider=FakeSpeechProvider(),
    )

    assert routed == []
    assert speeches == [(player, "我是人类玩家的公开发言", None)]


async def test_human_roundtable_context_includes_prior_public_speech_only() -> None:
    first = _human_player("player_1", "Human1")
    second = _human_player("player_2", "Human2")
    provider = CapturingSpeechProvider(
        [
            SpeechDecision.model_construct(
                public_speech="我是第一段公开发言",
                private_thought="只能自己知道的内心",
            ),
            SpeechDecision.model_construct(
                public_speech="我是第二段公开发言",
                private_thought=None,
            ),
        ]
    )
    hub = InformationHub()
    hub.set_context_provider(
        build_observation=lambda _player: "filtered observation",
        get_alive_players=lambda: [first, second],
    )

    routed = await hub.run_roundtable(
        [first, second],
        channel=VisibilityChannel.PUBLIC,
        context_builder=lambda speaker: f"context for {speaker.name}",
        instruction="请发言",
        phase="day_discussion",
        round_number=1,
        opening_announcement="主持人开场说明",
        human_input_provider=provider,
    )

    assert routed == []
    assert len(provider.contexts) == 2
    assert "【本轮已公开发言】" in provider.contexts[0]
    assert "主持人开场说明" in provider.contexts[0]
    assert "Human1: 我是第一段公开发言" not in provider.contexts[0]
    assert "【本轮已公开发言】" in provider.contexts[1]
    assert "主持人开场说明" in provider.contexts[1]
    assert "Human1: 我是第一段公开发言" in provider.contexts[1]
    assert "只能自己知道的内心" not in provider.contexts[1]


async def test_llm_roundtable_context_includes_prior_human_public_speech(
    monkeypatch,
) -> None:
    human = _human_player("player_1", "Human")
    bot = _demo_player("player_2", "Bot")
    provider = CapturingSpeechProvider(
        [
            SpeechDecision.model_construct(
                public_speech="human public speech",
                private_thought="human private thought",
            )
        ]
    )
    captured_contexts: list[str] = []

    async def fake_request_speech(
        _agent,
        context: str,
        _instruction: str,
        *,
        roundtable_phase,
    ) -> SpeechDecision:
        captured_contexts.append(context)
        return SpeechDecision.model_construct(
            public_speech="bot response",
            private_thought="bot private thought",
        )

    monkeypatch.setattr(WerewolfAdapterBridge, "request_speech", fake_request_speech)

    hub = InformationHub()
    hub.set_context_provider(
        build_observation=lambda _player: "filtered observation",
        get_alive_players=lambda: [human, bot],
    )

    routed = await hub.run_roundtable(
        [human, bot],
        channel=VisibilityChannel.PUBLIC,
        context_builder=lambda speaker: f"context for {speaker.name}",
        instruction="speak",
        phase="day_discussion",
        round_number=1,
        opening_announcement="opening public note",
        human_input_provider=provider,
    )

    assert routed == []
    assert captured_contexts
    assert "【本轮已公开发言】" in captured_contexts[0]
    assert "opening public note" in captured_contexts[0]
    assert "Human: human public speech" in captured_contexts[0]
    assert "human private thought" not in captured_contexts[0]


async def test_vote_intention_context_includes_public_transcript(
    monkeypatch,
) -> None:
    human = _human_player("player_1", "Human")
    observer = _demo_player("player_2", "Bot")
    captured_contexts: list[str] = []

    async def fake_request_vote_intention(
        _agent,
        _role_name: str,
        player,
        _targets,
        context: str,
        **_kwargs,
    ) -> VoteIntentionEntry:
        captured_contexts.append(context)
        return VoteIntentionEntry(
            player_id=player.player_id,
            player_name=player.name,
            seat=0,
            target_id=None,
            target_name=None,
            reason="no vote yet",
        )

    monkeypatch.setattr(
        WerewolfAdapterBridge,
        "request_vote_intention",
        fake_request_vote_intention,
    )

    hub = InformationHub()
    hub.set_context_provider(
        build_observation=lambda _player: "filtered observation",
        get_alive_players=lambda: [human, observer],
    )

    intentions = await hub._collect_vote_intentions(
        [observer],
        anchor=VoteIntentionAnchor.AFTER_SPEECH,
        context_builder=lambda _observer: "base voting context",
        phase="day_discussion",
        round_number=1,
        last_speaker=human,
        public_transcript=[
            "opening public note",
            "Human: human public speech",
        ],
    )

    assert set(intentions) == {observer.player_id}
    assert captured_contexts
    assert "base voting context" in captured_contexts[0]
    assert "【本轮已公开发言】" in captured_contexts[0]
    assert "Human: human public speech" in captured_contexts[0]
    assert "human private thought" not in captured_contexts[0]


async def test_phase_interaction_passes_human_provider_to_roundtable_hub() -> None:
    player = _human_player()
    hub = AsyncMock()
    hub.run_roundtable.return_value = []
    provider = FakeSpeechProvider()
    interaction = PhaseInteraction(hub, human_input_provider=provider)

    routed = await interaction.run_roundtable(
        [player],
        channel=VisibilityChannel.PUBLIC,
        context_builder=lambda _speaker: "context",
        instruction="请发言",
        phase="day_discussion",
        round_number=1,
    )

    assert routed == []
    hub.run_roundtable.assert_awaited_once()
    assert hub.run_roundtable.await_args.kwargs["human_input_provider"] is provider
