"""Step-pump control gate + last_night capture + /control endpoint."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.agent_team.communication.information_hub import InformationHub
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.interface.api.services.game_sessions import GameSession


def _session(tmp_path: Path) -> GameSession:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    return GameSession(
        run_id="run-x",
        run_dir=run_dir,
        config_path=tmp_path / "cfg.yaml",
        config_id="demo-6",
    )


def _engine_in_night(seed: int = 7) -> GameEngine:
    config = create_game_config_from_player_count(6)
    # InformationHub is required so DemoAgent decisions can be collected when a
    # phase actually runs (mirrors _run_game's information_hub wiring).
    engine = GameEngine(config, information_hub=InformationHub())
    engine.on_event = lambda _event: None
    players = [DemoAgent(name=f"P{i}", model="demo", seed=seed) for i in range(6)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)
    engine.game_state.set_phase(GamePhase.NIGHT)
    return engine


def test_session_defaults_playing_speed_one(tmp_path: Path) -> None:
    session = _session(tmp_path)
    assert session.gate.is_set() is True       # default = playing
    assert session.step_once is False
    assert session.speed == 1
    assert session.last_night == {}


def test_capture_phase_snapshot_records_night_results(tmp_path: Path) -> None:
    session = _session(tmp_path)
    engine = _engine_in_night()
    session.engine = engine
    gs = engine.game_state
    victim = gs.players[0].player_id
    guarded = gs.players[1].player_id
    gs.werewolf_target = victim
    gs.guard_protected = guarded
    gs.night_deaths.add(victim)
    gs.death_causes[victim] = "wolf_kill"

    session.capture_phase_snapshot()

    ln = session.last_night
    assert ln["deaths"] == [{"seat": 1, "cause": "wolf_kill"}]
    assert ln["guarded_seat"] == 2
    assert ln["saved_seat"] is None
    assert ln["poisoned_seat"] is None


def test_capture_phase_snapshot_survives_next_phase_clear(tmp_path: Path) -> None:
    session = _session(tmp_path)
    engine = _engine_in_night()
    session.engine = engine
    gs = engine.game_state
    gs.werewolf_target = gs.players[2].player_id
    gs.night_deaths.add(gs.players[2].player_id)
    gs.death_causes[gs.players[2].player_id] = "wolf_kill"

    session.capture_phase_snapshot()
    # simulate DAY_VOTING -> NIGHT clear
    gs.set_phase(GamePhase.DAY_VOTING)
    gs.next_phase()

    assert gs.werewolf_target is None            # engine cleared it
    assert session.last_night["deaths"] == [{"seat": 3, "cause": "wolf_kill"}]  # capture survived


@pytest.mark.asyncio
async def test_run_step_pump_completes_game(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import random
    from llm_werewolf.interface.api.services.game_sessions import GameSessionManager

    random.seed(99)
    session = _session(tmp_path)
    engine = GameEngine(
        create_game_config_from_player_count(6), information_hub=InformationHub()
    )
    events: list = []
    engine.on_event = events.append
    players = [DemoAgent(name=f"P{i}", model="demo", seed=99) for i in range(6)]
    roles = create_roles(role_names=engine.config.role_names)
    engine.setup_game(players=players, roles=roles)
    session.engine = engine

    # zero dwell so the test does not sleep
    result = await GameSessionManager._run_step_pump(session, dwell=0.0)

    assert session.engine.game_state.phase == GamePhase.ENDED
    assert isinstance(result, str) and result
    ended = [e for e in events if e.event_type.value == "game_ended"]
    assert len(ended) == 1


@pytest.mark.asyncio
async def test_step_pump_pause_halts_after_current_phase(tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import GameSessionManager

    session = _session(tmp_path)
    engine = _engine_in_night(seed=5)
    engine.game_state.set_phase(GamePhase.SETUP)
    session.engine = engine
    session.gate.clear()  # paused

    pump = asyncio.create_task(GameSessionManager._run_step_pump(session, dwell=0.0))
    await asyncio.sleep(0.05)
    assert not pump.done()                       # blocked on the gate, no phase ran
    assert engine.game_state.phase == GamePhase.SETUP
    pump.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pump


@pytest.mark.asyncio
async def test_step_pump_single_step_runs_one_phase(tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import GameSessionManager

    session = _session(tmp_path)
    engine = GameEngine(
        create_game_config_from_player_count(6), information_hub=InformationHub()
    )
    engine.on_event = lambda _e: None
    players = [DemoAgent(name=f"P{i}", model="demo", seed=3) for i in range(6)]
    roles = create_roles(role_names=engine.config.role_names)
    engine.setup_game(players=players, roles=roles)
    session.engine = engine
    session.gate.clear()
    session.step_once = True
    session.gate.set()  # request exactly one phase

    pump = asyncio.create_task(GameSessionManager._run_step_pump(session, dwell=0.0))
    await asyncio.sleep(0.05)
    assert engine.game_state.phase == GamePhase.NIGHT   # SETUP -> NIGHT, one phase
    assert session.gate.is_set() is False               # auto-paused
    pump.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pump
