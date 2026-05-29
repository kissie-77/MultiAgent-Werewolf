"""game_runtime/game_state.py 的测试。"""

from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState


def _players() -> list[Player]:
    return [
        Player("w1", "Wolf", Werewolf),
        Player("v1", "Villager1", Villager),
        Player("v2", "Villager2", Villager),
    ]


def test_next_phase_setup_to_night() -> None:
    state = GameState(_players())
    assert state.phase == GamePhase.SETUP
    state.next_phase()
    assert state.phase == GamePhase.NIGHT
    assert state.round_number == 1


def test_next_phase_first_night_to_sheriff_election() -> None:
    state = GameState(_players())
    state.phase = GamePhase.NIGHT
    state.round_number = 1
    state.enable_sheriff = True
    state.next_phase()
    assert state.phase == GamePhase.SHERIFF_ELECTION


def test_next_phase_first_night_skips_sheriff_when_disabled() -> None:
    state = GameState(_players())
    state.phase = GamePhase.NIGHT
    state.round_number = 1
    state.enable_sheriff = False
    state.sheriff_election_done = True
    state.next_phase()
    assert state.phase == GamePhase.DAY_DISCUSSION


def test_next_phase_voting_increments_round_and_clears_state() -> None:
    state = GameState(_players())
    state.phase = GamePhase.DAY_VOTING
    state.round_number = 2
    state.werewolf_target = "v1"
    state.votes = {"v2": "w1"}
    state.raven_marked = "v2"

    state.next_phase()

    assert state.phase == GamePhase.NIGHT
    assert state.round_number == 3
    assert state.werewolf_target is None
    assert state.votes == {}
    assert state.raven_marked is None


def test_get_vote_counts_with_raven_mark() -> None:
    state = GameState(_players())
    state.add_vote("v1", "w1")
    state.add_vote("v2", "w1")
    state.raven_marked = "w1"

    counts = state.get_vote_counts()
    assert counts["w1"] == 3.0


def test_sheriff_lifecycle() -> None:
    state = GameState(_players())
    state.set_sheriff("v1")
    sheriff = state.get_sheriff()
    assert sheriff is not None
    assert sheriff.is_sheriff()
    assert state.has_sheriff()

    state.remove_sheriff()
    assert state.sheriff_id is None
    assert not sheriff.is_sheriff()


def test_reset_deaths() -> None:
    state = GameState(_players())
    state.night_deaths.add("v1")
    state.death_causes["v1"] = "werewolf"
    state.reset_deaths()
    assert state.night_deaths == set()
    assert state.death_causes == {}
