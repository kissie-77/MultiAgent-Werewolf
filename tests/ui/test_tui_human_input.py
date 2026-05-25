from llm_werewolf.ui.tui_human_input import TextualHumanInputProvider
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager


class FakeTUIInputApp:
    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.prompts: list[tuple[str, str]] = []
        self.feedback: list[str] = []

    async def request_human_input(self, prompt: str, *, mode: str) -> str:
        self.prompts.append((prompt, mode))
        return self.answers.pop(0)

    def show_human_feedback(self, message: str) -> None:
        self.feedback.append(message)


def _players() -> list[Player]:
    return [
        Player("player_1", "Human", Villager),
        Player("player_2", "Bot2", Villager),
        Player("player_3", "Bot3", Villager),
    ]


async def test_textual_provider_retries_until_valid_seat() -> None:
    app = FakeTUIInputApp("abc", "9", "2")
    provider = TextualHumanInputProvider(app)
    targets = _players()[1:]

    selected = await provider.choose_seat(
        role_name="Guard",
        action_description="Choose a target",
        possible_targets=targets,
        allow_skip=False,
        context="Night action",
    )

    assert selected == targets[0]
    assert [mode for _, mode in app.prompts] == ["number", "number", "number"]
    assert app.feedback == [
        "请输入数字编号。",
        "编号不在可选范围内，请重试。",
    ]
    assert app.prompts[0][0].splitlines()[0] == "输入目标编号：2=Bot2, 3=Bot3"


async def test_textual_provider_witch_prompt_shows_actions_first() -> None:
    app = FakeTUIInputApp("1")
    provider = TextualHumanInputProvider(app)

    decision = await provider.choose_witch_action(
        role_name="Witch",
        can_see_victim=True,
        victim_line="今晚狼人刀口：Human（1号）。",
        poison_targets=_players()[1:],
        context="解药：可用。毒药：可用。",
    )

    assert decision.action == "save"
    assert app.prompts[0][0].splitlines()[0] == (
        "女巫行动：1=使用解药，2=使用毒药，3=不行动"
    )


async def test_textual_provider_speak_accepts_plain_text() -> None:
    app = FakeTUIInputApp("", "I want to hear from seat 3 first.")
    provider = TextualHumanInputProvider(app)

    decision = await provider.speak(
        context="Day discussion",
        instruction="Speak now",
        phase="day_discussion",
        round_number=1,
    )

    assert decision.public_speech == "I want to hear from seat 3 first."
    assert decision.private_thought is None
    assert [mode for _, mode in app.prompts] == ["text", "text"]
    assert app.feedback == ["发言不能为空。"]
