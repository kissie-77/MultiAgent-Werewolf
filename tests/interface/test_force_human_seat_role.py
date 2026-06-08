"""Regression: forcing the human's chosen seat-role must keep each role instance's
``self.player`` back-reference pointing at its OWN player.

Bug (finding #1): ``_force_human_seat_role`` swapped the role *instances* between the
human seat and the donor seat but never re-pointed ``role.player``. The night layer
resolves the acting player + agent via ``role.player`` / ``role.player.agent``
(see ``game_runtime/registries/role_night_plans.py``), so a crossed back-reference
routed one role's prompt to the wrong seat's agent — e.g. a human who picked Seer was
shown the LLM Witch's night prompt (the human's web-human broker was reached via the
Witch instance's stale ``.player``).
"""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.cli.runtime.bootstrap import (
    create_information_hub,
    prepare_game_roster,
)
from llm_werewolf.interface.api.services.game_sessions import _force_human_seat_role

_CONFIGS = Path(__file__).resolve().parents[2] / "configs"


def _build_engine(seed: int = 1234) -> GameEngine:
    cfg = load_config(config_path=_CONFIGS / "demo-6.yaml")
    players, roles, game_config = prepare_game_roster(cfg)
    engine = GameEngine(
        game_config, language=cfg.language, information_hub=create_information_hub()
    )
    engine.setup_game(players=players, roles=roles, role_shuffle_seed=seed)
    return engine


def _role_name(player: object) -> str:
    return str(player.role.get_config().name)


def test_force_human_seat_role_keeps_role_player_backref_consistent() -> None:
    engine = _build_engine()
    players = engine.game_state.players
    seat1_name = _role_name(players[0])
    # Donor = first OTHER seat whose dealt role differs from seat 1's (guarantees a swap).
    donor = next(p for p in players[1:] if _role_name(p) != seat1_name)
    requested = _role_name(donor)

    _force_human_seat_role(engine, seat=1, requested=requested)

    # Human seat now actually holds the requested role.
    assert _role_name(players[0]) == requested
    # And EVERY role instance's back-reference points at its own player — so the night
    # layer (which uses role.player / role.player.agent) routes to the correct seat.
    for p in players:
        assert p.role.player is p, f"{p.player_id}: role.player back-ref crossed"
