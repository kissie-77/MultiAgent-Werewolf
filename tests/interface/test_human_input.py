from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.interface.human_input import ShellHumanInputProvider, is_human_agent
from llm_werewolf.agent_team.base import HumanAgent, DemoAgent


def _players() -> list[Player]:
    return [
        Player("player_1", "Human", Villager),
        Player("player_2", "Bot2", Villager),
        Player("player_3", "Bot3", Villager),
    ]


def _provider_with_answers(*answers: str) -> ShellHumanInputProvider:
    iterator = iter(answers)
    return ShellHumanInputProvider(
        input_fn=lambda _prompt: next(iterator),
        write_fn=lambda _line: None,
    )


async def test_choose_seat_retries_until_valid_seat() -> None:
    provider = _provider_with_answers("abc", "9", "2")
    targets = _players()[1:]

    selected = await provider.choose_seat(
        role_name="Guard",
        action_description="选择一名玩家守护",
        possible_targets=targets,
        allow_skip=False,
        context="你是守卫。",
    )

    assert selected == targets[0]


async def test_choose_seat_returns_none_when_skip_allowed() -> None:
    provider = _provider_with_answers("0")

    selected = await provider.choose_seat(
        role_name="Villager",
        action_description="投票",
        possible_targets=_players()[1:],
        allow_skip=True,
        context="白天投票。",
    )

    assert selected is None


async def test_speak_accepts_plain_short_text_without_brackets() -> None:
    provider = _provider_with_answers("我觉得2号比较可疑")

    decision = await provider.speak(
        context="白天讨论。",
        instruction="请发言。",
        phase="day_discussion",
        round_number=1,
    )

    assert decision.public_speech == "我觉得2号比较可疑"
    assert decision.private_thought is None


async def test_choose_yes_no_uses_numbered_options() -> None:
    provider = _provider_with_answers("x", "2")

    selected = await provider.choose_yes_no(
        role_name="Blood Moon Apostle",
        question="是否变身？",
        context="队友已阵亡。",
    )

    assert selected is False


async def test_choose_witch_action_poison_then_target() -> None:
    provider = _provider_with_answers("2", "3")
    targets = _players()[1:]

    decision = await provider.choose_witch_action(
        role_name="Witch",
        can_see_victim=True,
        victim_line="今晚狼人刀口：Bot2（2号）。",
        poison_targets=targets,
        context="解药：可用。毒药：可用。",
    )

    assert decision.action == "poison"
    assert decision.seat == 3


async def test_choose_multi_targets_collects_distinct_targets() -> None:
    provider = _provider_with_answers("2", "2", "3")
    targets = _players()

    selected = await provider.choose_multi_targets(
        role_name="Cupid",
        action_description="选择两名玩家结为情侣",
        possible_targets=targets,
        num_targets=2,
        context="首夜行动。",
    )

    assert [player.player_id for player in selected] == ["player_2", "player_3"]


def test_is_human_agent_checks_model_name() -> None:
    assert is_human_agent(HumanAgent(name="Human", model="human"))
    assert not is_human_agent(DemoAgent(name="Bot", model="demo"))
    assert not is_human_agent(None)
