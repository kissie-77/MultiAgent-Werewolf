"""Human seat picks a role -> that seat actually gets it (post-deal swap).

Covers the "选狼人却进成预言家" bug: setup_game shuffles roles, so the human's
chosen role used to be random. `_force_human_seat_role` swaps it onto the seat
while preserving the role multiset (board balance).
"""

from llm_werewolf.interface.api.services.game_sessions import (
    _role_matches,
    _force_human_seat_role,
)


class _Cfg:
    def __init__(self, name: str, display_name: str) -> None:
        self.name = name
        self.display_name = display_name


class _Role:
    def __init__(self, name: str, display_name: str) -> None:
        self._cfg = _Cfg(name, display_name)

    def get_config(self) -> _Cfg:
        return self._cfg


class _Agent:
    def __init__(self) -> None:
        self.bound: tuple[type, int] | None = None

    def bind_role(self, role_class: type, seat_number: int) -> None:
        self.bound = (role_class, seat_number)


class _Player:
    def __init__(self, role: _Role) -> None:
        self.role = role
        self.agent = _Agent()


class _Engine:
    def __init__(self, roles: list[_Role]) -> None:
        self.game_state = type("GS", (), {"players": [_Player(r) for r in roles]})()


def _roles(engine: _Engine) -> list[str]:
    return [p.role.get_config().name for p in engine.game_state.players]


def _lineup() -> list[_Role]:
    return [
        _Role("Seer", "预言家"),
        _Role("Werewolf", "狼人"),
        _Role("Villager", "平民"),
        _Role("Witch", "女巫"),
        _Role("Werewolf", "狼人"),
        _Role("Hunter", "猎人"),
    ]


def test_chosen_role_swapped_onto_human_seat_by_zh_name() -> None:
    eng = _Engine(_lineup())  # seat 1 is Seer
    _force_human_seat_role(eng, seat=1, requested="狼人")
    assert eng.game_state.players[0].role.get_config().name == "Werewolf"
    # multiset preserved (a swap, not a substitution)
    assert sorted(_roles(eng)) == sorted(
        ["Seer", "Werewolf", "Villager", "Witch", "Werewolf", "Hunter"]
    )


def test_matches_english_key_too() -> None:
    eng = _Engine(_lineup())
    _force_human_seat_role(eng, seat=1, requested="Witch")
    assert eng.game_state.players[0].role.get_config().name == "Witch"


def test_already_correct_is_noop() -> None:
    eng = _Engine(_lineup())
    before = _roles(eng)
    _force_human_seat_role(eng, seat=1, requested="预言家")  # seat 1 already Seer
    assert _roles(eng) == before


def test_role_not_in_lineup_keeps_deal() -> None:
    eng = _Engine(_lineup())
    before = _roles(eng)
    _force_human_seat_role(eng, seat=1, requested="守墓人")  # not dealt
    assert _roles(eng) == before  # unchanged, no crash


def test_swapped_agents_are_rebound() -> None:
    eng = _Engine(_lineup())  # seat1 Seer, a Werewolf at seat 2
    _force_human_seat_role(eng, seat=1, requested="狼人")
    human_agent = eng.game_state.players[0].agent
    assert human_agent.bound is not None and human_agent.bound[1] == 1


def test_none_seat_or_empty_role_is_noop() -> None:
    eng = _Engine(_lineup())
    before = _roles(eng)
    _force_human_seat_role(eng, seat=None, requested="狼人")
    _force_human_seat_role(eng, seat=1, requested=None)
    _force_human_seat_role(eng, seat=1, requested="")
    assert _roles(eng) == before


def test_role_matches_helper() -> None:
    wolf = _Role("Werewolf", "狼人")
    assert _role_matches(wolf, "狼人")
    assert _role_matches(wolf, "werewolf")
    assert not _role_matches(wolf, "预言家")
