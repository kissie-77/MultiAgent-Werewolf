from unittest.mock import AsyncMock

from llm_werewolf.agent_team.base import HumanAgent
from llm_werewolf.agent_team.information_hub import InformationHub
from llm_werewolf.agent_team.visibility import VisibilityChannel
from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.strategy.decisions import SpeechDecision


class FakeSpeechProvider:
    async def speak(self, **_kwargs):
        return SpeechDecision.model_construct(
            public_speech="我是人类玩家的公开发言",
            private_thought=None,
        )


def _human_player() -> Player:
    agent = HumanAgent(name="Human", model="human")
    return Player("player_1", "Human", Villager, agent=agent, ai_model="human")


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
