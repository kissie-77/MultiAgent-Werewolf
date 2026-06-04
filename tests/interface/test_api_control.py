"""Step-pump control gate + last_night capture + /control endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
import asyncio

import pytest

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.interface.api.services.game_sessions import GameSession
from llm_werewolf.agent_team.communication.information_hub import InformationHub

if TYPE_CHECKING:
    from pathlib import Path


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
    # Capture runs AFTER step() has advanced the phase out of NIGHT (the real
    # pump ordering): night data is still present in the DAY phases.
    gs.set_phase(GamePhase.DAY_DISCUSSION)

    session.capture_phase_snapshot()

    ln = session.last_night
    assert ln["deaths"] == [{"seat": 1, "cause": "wolf_kill"}]
    assert ln["guarded_seat"] == 2
    assert ln["saved_seat"] is None
    assert ln["poisoned_seat"] is None


def test_capture_phase_snapshot_noop_while_phase_is_night(tmp_path: Path) -> None:
    """While phase is NIGHT the resolution has not produced final deaths yet, and
    the previous-night data has been cleared at NIGHT entry; capture is a no-op.
    """
    session = _session(tmp_path)
    engine = _engine_in_night()
    session.engine = engine
    gs = engine.game_state
    gs.night_deaths.add(gs.players[0].player_id)
    gs.death_causes[gs.players[0].player_id] = "wolf_kill"

    assert gs.get_phase() == GamePhase.NIGHT
    session.capture_phase_snapshot()

    assert session.last_night == {}              # no capture while still NIGHT


def test_capture_phase_snapshot_survives_next_phase_clear(tmp_path: Path) -> None:
    session = _session(tmp_path)
    engine = _engine_in_night()
    session.engine = engine
    gs = engine.game_state
    gs.werewolf_target = gs.players[2].player_id
    gs.night_deaths.add(gs.players[2].player_id)
    gs.death_causes[gs.players[2].player_id] = "wolf_kill"
    gs.set_phase(GamePhase.DAY_DISCUSSION)       # post-resolution phase (real ordering)

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
    assert isinstance(result, str)
    assert result
    ended = [e for e in events if e.event_type.value == "game_ended"]
    assert len(ended) == 1


@pytest.mark.asyncio
async def test_step_pump_captures_last_night_from_real_pump(
    tmp_path: Path,
) -> None:
    """Drive the REAL pump (capture runs after step() advances the phase) and
    assert session.last_night reflects the actual resolved night_deaths.

    Regression guard: capture_phase_snapshot must NOT require phase==NIGHT,
    because by the time the pump calls it the engine has already advanced past
    NIGHT (NIGHT branch of step() runs next_phase() before returning).
    """
    import random

    from llm_werewolf.interface.api.services.game_sessions import GameSessionManager

    random.seed(99)
    session = _session(tmp_path)
    engine = GameEngine(
        create_game_config_from_player_count(6), information_hub=InformationHub()
    )
    engine.on_event = lambda _e: None
    players = [DemoAgent(name=f"P{i}", model="demo", seed=99) for i in range(6)]
    roles = create_roles(role_names=engine.config.role_names)
    engine.setup_game(players=players, roles=roles)
    session.engine = engine

    # Pump a single step at a time so we can observe capture after a resolved
    # night while the game is still mid-flight (seed 99 -> player_6 dies night 1).
    gs = engine.game_state
    while gs.phase != GamePhase.DAY_DISCUSSION and not engine.is_over():
        await engine.step()
        session.capture_phase_snapshot()

    assert sorted(gs.night_deaths) == ["player_6"]      # actual resolved death
    assert session.last_night != {}                      # capture happened
    assert session.last_night["deaths"] == [{"seat": 6, "cause": "werewolf"}]

    # Run to completion via the real pump; final night kill must surface too.
    result = await GameSessionManager._run_step_pump(session, dwell=0.0)
    assert gs.phase == GamePhase.ENDED
    assert isinstance(result, str)
    assert result
    assert session.last_night["deaths"]                  # non-empty at game end
    assert all(d["seat"] is not None for d in session.last_night["deaths"])


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


@pytest.mark.asyncio
async def test_control_pause_resume_step_speed(tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import (
        GameSessionStatus,
        GameSessionManager,
    )

    mgr = GameSessionManager()
    session = _session(tmp_path)
    engine = _engine_in_night(seed=11)
    session.engine = engine
    session.status = GameSessionStatus.RUNNING
    mgr._sessions[session.run_id] = session

    paused = await mgr.control(session.run_id, action="pause")
    assert paused.play_state == "paused"
    assert session.gate.is_set() is False
    assert paused.phase == "night"

    resumed = await mgr.control(session.run_id, action="resume")
    assert resumed.play_state == "playing"
    assert session.gate.is_set() is True

    stepped = await mgr.control(session.run_id, action="step")
    assert stepped.play_state == "playing"
    assert session.step_once is True
    assert session.gate.is_set() is True

    sped = await mgr.control(session.run_id, action="speed", value=4)
    assert sped.speed == 4
    assert session.speed == 4


@pytest.mark.asyncio
async def test_control_unknown_run_returns_none(tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import GameSessionManager

    mgr = GameSessionManager()
    assert await mgr.control("nope", action="pause") is None


@pytest.mark.asyncio
async def test_control_rejects_bad_speed(tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import GameSessionManager

    mgr = GameSessionManager()
    session = _session(tmp_path)
    session.engine = _engine_in_night()
    mgr._sessions[session.run_id] = session
    with pytest.raises(ValueError):
        await mgr.control(session.run_id, action="speed", value=3)


def test_control_endpoint_unknown_run_404(api_client) -> None:
    resp = api_client.post(
        "/api/v1/games/not-started/control", json={"action": "pause"}
    )
    assert resp.status_code == 404


def test_control_endpoint_pause(api_client, tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import (
        GameSessionStatus,
        game_session_manager,
    )

    run_dir = tmp_path / "ctrl-run"
    run_dir.mkdir()
    session = GameSession(
        run_id="ctrl-run",
        run_dir=run_dir,
        config_path=tmp_path / "cfg.yaml",
        config_id="demo-6",
    )
    session.engine = _engine_in_night(seed=21)
    session.status = GameSessionStatus.RUNNING
    game_session_manager._sessions["ctrl-run"] = session

    resp = api_client.post(
        "/api/v1/games/ctrl-run/control", json={"action": "pause"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"] == "ctrl-run"
    assert data["play_state"] == "paused"
    assert data["phase"] == "night"


def test_control_endpoint_rejects_bad_speed(api_client, tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import game_session_manager

    run_dir = tmp_path / "ctrl-run2"
    run_dir.mkdir()
    session = GameSession(
        run_id="ctrl-run2",
        run_dir=run_dir,
        config_path=tmp_path / "cfg.yaml",
        config_id="demo-6",
    )
    session.engine = _engine_in_night(seed=22)
    game_session_manager._sessions["ctrl-run2"] = session

    resp = api_client.post(
        "/api/v1/games/ctrl-run2/control", json={"action": "speed", "value": 3}
    )
    assert resp.status_code == 422  # pydantic request validation rejects value=3


@pytest.mark.asyncio
async def test_state_reports_play_state_speed_and_last_night(tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import (
        GameSessionStatus,
        GameSessionManager,
    )

    mgr = GameSessionManager()
    session = _session(tmp_path)
    engine = _engine_in_night(seed=31)
    session.engine = engine
    session.status = GameSessionStatus.RUNNING
    gs = engine.game_state
    gs.werewolf_target = gs.players[0].player_id
    gs.night_deaths.add(gs.players[0].player_id)
    gs.death_causes[gs.players[0].player_id] = "wolf_kill"
    gs.set_phase(GamePhase.DAY_DISCUSSION)   # post-resolution phase (real ordering)
    session.capture_phase_snapshot()
    session.gate.clear()   # paused
    session.speed = 2
    mgr._sessions[session.run_id] = session

    state = mgr.get_state(
        session.run_id,
        runs_dir=tmp_path,
        eval_runs_dir=tmp_path,
    )
    assert state is not None
    # status collapses to "paused" because the gate is cleared on a RUNNING session
    assert state.status == "paused"
    assert state.play_state == "paused"
    assert state.speed == 2
    # ATTRIBUTE access against the typed LastNight model (NOT dict subscript)
    assert [d.model_dump() for d in state.last_night.deaths] == [
        {"seat": 1, "cause": "wolf_kill"}
    ]


@pytest.mark.asyncio
async def test_state_surfaces_sub_phase_and_actor_seat(tmp_path: Path) -> None:
    from llm_werewolf.interface.api.services.game_sessions import (
        GameSessionManager,
        GameSessionStatus,
    )

    mgr = GameSessionManager()
    session = _session(tmp_path)
    session.engine = _engine_in_night(seed=41)
    session.status = GameSessionStatus.RUNNING
    session.current_sub_phase = "witch_decide"
    session.current_actor_seat = 3
    mgr._sessions[session.run_id] = session

    state = mgr.get_state(session.run_id, runs_dir=tmp_path, eval_runs_dir=tmp_path)
    assert state is not None
    assert state.sub_phase == "witch_decide"
    assert state.current_actor_seat == 3
