"""狼队频道和未同醒狼人支持者的信息隔离。"""

import pytest

from llm_werewolf.game_runtime.roles import Villager, Werewolf, BloodMoonApostle
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.registries.role_night_plans import _plan_werewolf_pack_vote


class _DummyAgent:
    pass


class _RecordingInteraction:
    def __init__(self) -> None:
        self.possible_targets = []
        self.additional_context = ""

    async def request_seat_choice(self, *_args, **kwargs):
        self.possible_targets = kwargs["possible_targets"]
        self.additional_context = kwargs["additional_context"]
        return None


@pytest.mark.asyncio
async def test_werewolf_vote_does_not_reveal_untransformed_blood_moon_as_teammate() -> None:
    wolf = Player("player_1", "狼人", Werewolf, agent=_DummyAgent())
    blood_moon = Player("player_2", "血月", BloodMoonApostle, agent=_DummyAgent())
    villager = Player("player_3", "村民", Villager, agent=_DummyAgent())
    game_state = GameState([wolf, blood_moon, villager])
    game_state.round_number = 1
    interaction = _RecordingInteraction()

    await _plan_werewolf_pack_vote(
        wolf.role,
        game_state,
        interaction,  # type: ignore[arg-type]
        role_name="Werewolf",
    )

    assert [p.player_id for p in interaction.possible_targets] == ["player_2", "player_3"]
    assert "血月" not in interaction.additional_context


def test_werewolf_private_notes_exclude_untransformed_blood_moon() -> None:
    wolf = Player("player_1", "狼人", Werewolf, agent=_DummyAgent())
    blood_moon = Player("player_2", "血月", BloodMoonApostle, agent=_DummyAgent())
    game_state = GameState([wolf, blood_moon])

    notes = "\n".join(wolf.get_private_notes(game_state))

    assert "血月" not in notes
