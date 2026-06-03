"""step()-pump must be behavior-equivalent to play_game()."""

from __future__ import annotations

import random

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.agent_team.communication.information_hub import InformationHub
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.game_runtime.types import EventType, GamePhase


def _build_engine(seed: int) -> GameEngine:
    random.seed(seed)
    config = create_game_config_from_player_count(6)
    # A real InformationHub is required: without it DemoAgent decisions cannot be
    # collected and play_game() never reaches a victory condition (it loops forever).
    # This mirrors _run_game's information_hub=create_information_hub() wiring.
    engine = GameEngine(config, information_hub=InformationHub())
    engine.on_event = lambda _event: None
    players = [
        DemoAgent(name=f"Player{i}", model="demo", seed=seed)
        for i in range(config.num_players)
    ]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)
    return engine


def _event_signature(engine: GameEngine) -> list[tuple[str, str]]:
    """Phase/round-bearing structural signature: only transition + terminal events."""
    sig: list[tuple[str, str]] = []
    for ev in engine.get_events():
        if ev.event_type in (EventType.PHASE_CHANGED, EventType.GAME_ENDED):
            sig.append((ev.event_type.value, ev.phase.value))
    return sig


def _outcome(engine: GameEngine) -> dict:
    gs = engine.game_state
    assert gs is not None
    return {
        "phase": gs.phase,
        "winner": gs.winner,
        "round": gs.round_number,
        "dead": sorted(p.player_id for p in gs.get_dead_players()),
    }


@pytest.mark.asyncio
async def test_step_pump_matches_play_game() -> None:
    seed = 20260603

    play_engine = _build_engine(seed)
    await play_engine.play_game()

    step_engine = _build_engine(seed)
    while not step_engine.is_over():
        await step_engine.step()

    assert _outcome(step_engine) == _outcome(play_engine)
    assert step_engine.game_state.phase == GamePhase.ENDED

    play_ended = [
        e for e in play_engine.get_events() if e.event_type == EventType.GAME_ENDED
    ]
    step_ended = [
        e for e in step_engine.get_events() if e.event_type == EventType.GAME_ENDED
    ]
    assert len(play_ended) == 1
    assert len(step_ended) == 1

    assert _event_signature(step_engine) == _event_signature(play_engine)


@pytest.mark.asyncio
async def test_step_setup_advances_to_night_without_placeholders() -> None:
    engine = _build_engine(20260603)
    assert engine.game_state.phase == GamePhase.SETUP

    messages = await engine.step()

    assert engine.game_state.phase == GamePhase.NIGHT
    assert engine.game_state.round_number == 1
    joined = "\n".join(messages)
    assert "Press 'n'" not in joined
    assert "Game initialized" not in joined


@pytest.mark.asyncio
async def test_step_resets_deaths_at_night_entry() -> None:
    engine = _build_engine(20260603)
    await engine.step()  # SETUP -> NIGHT (no resolution yet)
    engine.game_state.night_deaths.add("stale_player")
    engine.game_state.death_causes["stale_player"] = "stale"

    # Next NIGHT step must clear the stale deaths before resolving this night.
    assert engine.game_state.phase == GamePhase.NIGHT
    await engine.step()  # runs the NIGHT phase
    assert "stale_player" not in engine.game_state.night_deaths
    assert "stale_player" not in engine.game_state.death_causes
