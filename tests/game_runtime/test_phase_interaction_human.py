from unittest.mock import AsyncMock

from llm_werewolf.agent_team.base import DemoAgent, HumanAgent
from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.strategy.decisions import SpeechDecision, WitchNightDecision


class FakeHumanInputProvider:
    def __init__(self, target):
        self.target = target

    async def choose_seat(self, **_kwargs):
        return self.target

    async def choose_yes_no(self, **_kwargs):
        return True

    async def choose_witch_action(self, **_kwargs):
        return WitchNightDecision(action="none", seat=0, reason=None)

    async def choose_multi_targets(self, **_kwargs):
        return [self.target]

    async def speak(self, **_kwargs):
        return SpeechDecision.model_construct(public_speech="我是人类发言", private_thought=None)


def _player(player_id: str, name: str, agent):
    return Player(player_id, name, Villager, agent=agent, ai_model=agent.model)


async def test_human_seat_choice_uses_provider_not_hub() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    interaction = PhaseInteraction(hub)
    interaction.set_human_input_provider(FakeHumanInputProvider(target))

    selected = await interaction.request_seat_choice(
        human,
        human.agent,
        "Guard",
        "守护一名玩家",
        [target],
    )

    assert selected == target
    hub.request_private_seat_choice.assert_not_called()


async def test_llm_seat_choice_still_uses_hub() -> None:
    actor = _player("player_1", "Bot1", DemoAgent(name="Bot1", model="demo"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    hub.request_private_seat_choice.return_value = target
    interaction = PhaseInteraction(hub)

    selected = await interaction.request_seat_choice(
        actor,
        actor.agent,
        "Guard",
        "守护一名玩家",
        [target],
    )

    assert selected == target
    hub.request_private_seat_choice.assert_awaited_once()


async def test_human_speech_uses_provider() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    interaction = PhaseInteraction(AsyncMock())
    interaction.set_human_input_provider(FakeHumanInputProvider(target))

    decision = await interaction.request_speech(
        human,
        human.agent,
        context="白天讨论",
        instruction="请发言",
        phase="day_discussion",
        round_number=1,
    )

    assert decision.public_speech == "我是人类发言"


async def test_human_branch_without_provider_raises_clear_error() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    interaction = PhaseInteraction(AsyncMock())

    try:
        await interaction.request_yes_no(
            human,
            human.agent,
            role_name="Blood Moon Apostle",
            question="是否变身？",
        )
    except RuntimeError as exc:
        assert "HumanInputProvider" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
