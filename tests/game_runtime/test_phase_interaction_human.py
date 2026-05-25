from unittest.mock import AsyncMock

from llm_werewolf.agent_team.base import DemoAgent, HumanAgent
from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.strategy.decisions import SpeechDecision, WitchNightDecision


class FakeHumanInputProvider:
    def __init__(self, target):
        self.target = target
        self.calls = {}

    async def choose_seat(self, **kwargs):
        self.calls["choose_seat"] = kwargs
        return self.target

    async def choose_yes_no(self, **kwargs):
        self.calls["choose_yes_no"] = kwargs
        return True

    async def choose_witch_action(self, **kwargs):
        self.calls["choose_witch_action"] = kwargs
        return WitchNightDecision(action="none", seat=0, reason=None)

    async def choose_multi_targets(self, **kwargs):
        self.calls["choose_multi_targets"] = kwargs
        return [self.target]

    async def speak(self, **kwargs):
        self.calls["speak"] = kwargs
        return SpeechDecision.model_construct(public_speech="我是人类发言", private_thought=None)


def _player(player_id: str, name: str, agent):
    return Player(player_id, name, Villager, agent=agent, ai_model=agent.model)


async def test_human_seat_choice_uses_provider_not_hub() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    interaction = PhaseInteraction(hub)
    provider = FakeHumanInputProvider(target)
    interaction.set_human_input_provider(provider)

    selected = await interaction.request_seat_choice(
        human,
        human.agent,
        "Guard",
        "守护一名玩家",
        [target],
        allow_skip=True,
        additional_context="昨夜信息",
    )

    assert selected == target
    assert provider.calls["choose_seat"] == {
        "role_name": "Guard",
        "action_description": "守护一名玩家",
        "possible_targets": [target],
        "allow_skip": True,
        "context": "昨夜信息",
    }
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
    provider = FakeHumanInputProvider(target)
    interaction.set_human_input_provider(provider)

    decision = await interaction.request_speech(
        human,
        human.agent,
        context="白天讨论",
        instruction="请发言",
        phase="day_discussion",
        round_number=1,
    )

    assert decision.public_speech == "我是人类发言"
    assert provider.calls["speak"] == {
        "context": "白天讨论",
        "instruction": "请发言",
        "phase": "day_discussion",
        "round_number": 1,
    }


async def test_human_yes_no_uses_provider_kwargs() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    provider = FakeHumanInputProvider(target)
    interaction = PhaseInteraction(hub)
    interaction.set_human_input_provider(provider)

    answer = await interaction.request_yes_no(
        human,
        human.agent,
        role_name="Blood Moon Apostle",
        question="是否变身？",
        context="白天阶段",
    )

    assert answer is True
    assert provider.calls["choose_yes_no"] == {
        "role_name": "Blood Moon Apostle",
        "question": "是否变身？",
        "context": "白天阶段",
    }
    hub.request_private_yes_no.assert_not_called()


async def test_human_multi_targets_uses_provider_kwargs() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    provider = FakeHumanInputProvider(target)
    interaction = PhaseInteraction(hub)
    interaction.set_human_input_provider(provider)

    selected = await interaction.request_multi_targets(
        human,
        human.agent,
        role_name="Wolf King",
        action_description="选择两名玩家",
        possible_targets=[target],
        num_targets=1,
        additional_context="技能结算",
    )

    assert selected == [target]
    assert provider.calls["choose_multi_targets"] == {
        "role_name": "Wolf King",
        "action_description": "选择两名玩家",
        "possible_targets": [target],
        "num_targets": 1,
        "context": "技能结算",
    }
    hub.request_private_multi_target.assert_not_called()


async def test_human_witch_night_choice_uses_provider_kwargs() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    provider = FakeHumanInputProvider(target)
    interaction = PhaseInteraction(hub)
    interaction.set_human_input_provider(provider)

    decision = await interaction.request_witch_night_choice(
        human,
        human.agent,
        role_name="Witch",
        can_see_victim=True,
        victim_line="昨夜 player_2 被袭击",
        poison_targets=[target],
        additional_context="女巫行动",
    )

    assert decision.action == "none"
    assert provider.calls["choose_witch_action"] == {
        "role_name": "Witch",
        "can_see_victim": True,
        "victim_line": "昨夜 player_2 被袭击",
        "poison_targets": [target],
        "context": "女巫行动",
    }
    hub.request_private_witch_night.assert_not_called()


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
