# Engine-Driven Game API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the log-driven spectator projection with an engine-driven API — retained engine, step-pump with pause/resume/step/speed control, authoritative `GET /state`, SSE `GET /stream` with `Last-Event-ID` resume, and structured engine signals — so day/night phases, werewolf night chat, and every skill are surfaced from the engine's live state, not reverse-engineered from `events.jsonl`.

**Architecture:** Keep the GameEngine as the brain. `GameSession` retains the engine + a control gate + an in-memory EventHub. `_run_game` pumps `engine.step()` phase-by-phase, snapshotting between phases. `on_event` fans out to both `events.jsonl` (replay) and the EventHub (live SSE). The React frontend drives all UI off the authoritative `GamePhase` enum from `/state` and subscribes to `/stream`.

**Tech Stack:** Python 3 + FastAPI + Pydantic + asyncio + uv + pytest (backend); React 19 + TypeScript + Vite + Zustand + EventSource/SSE (frontend).

**Spec:** `docs/superpowers/specs/2026-06-03-engine-driven-game-api-design.md`

---

## M1 — Retain engine + GET /state (authoritative live snapshot + disk fallback)

**Coverage:** Covers spec §5.1 (GET /state authoritative live snapshot: status/error/play_state/speed/phase/round/winner/sheriff_seat/alive_count/dead_count/last_night/votes/cursor/players, with sub_phase/current_actor_seat declared here as null defaults and populated later by M4's fan-out tracking; play_state/speed/status-collapse/captured last_night populated by M2) and §6 item 1 (retain the engine: GameSession.engine field + session.engine set in _run_game). Implements the §8/§5.1 disk fallback for finished/evicted runs by reusing build_view and §10 milestone 1 ('Retain engine + /state — authoritative phase with zero loop change'). Reuses the existing synchronous serialize_game_state per the milestone constraint (no role_data widening — that is M3; no play_game loop change — that is M2). last_night is composed in the API layer from live snapshot fields (night_deaths/death_causes/witch_saved_target/guard_protected/witch_poison_target) per §6 item 8's 'or compose them in the API layer from live state'. Does NOT yet capture last_night between phases before next_phase() clears it (that timing belongs to M2's step-pump); on the live path last_night reflects current uncleared engine state. Control-gate fields play_state/speed are stubbed to playing/1 until M2 adds the gate.

**File structure:**

| File | Action | Responsibility |
|---|---|---|
| `src/llm_werewolf/interface/api/services/game_sessions.py` | modify | Add `engine` field to GameSession dataclass; set `session.engine = engine` in `_run_game` after setup; add `get_state(run_id, ...)` service method that serializes the live engine when the session is in memory and the engine exists, else falls back to disk via build_view. |
| `src/llm_werewolf/interface/api/models/state.py` | create | New Pydantic response models for GET /state: StatePlayer, LastNight, StateVotes, GameStateResponse matching the spec §5.1 field/enum names. |
| `src/llm_werewolf/interface/api/services/state.py` | create | Pure functions that compose a GameStateResponse from a live GameStateSnapshot (`build_state_from_snapshot`) and from a disk ViewResponse (`build_state_from_view`), reusing serialize_game_state output and build_view output respectively. |
| `src/llm_werewolf/interface/api/routes/actions.py` | modify | Add the GET /games/{run_id}/state route returning ApiResponse[GameStateResponse], 404 when the run is unknown, alongside the existing /view route. |
| `tests/interface/test_state_service.py` | create | Unit tests for build_state_from_snapshot (live) and build_state_from_view (disk fallback), and for GameSession.engine wiring. |
| `tests/interface/test_api_state.py` | create | Route-level tests for GET /api/v1/games/{run_id}/state (disk fallback for a finished run, 404 for missing run). |

**Goal:** keep the live engine on `GameSession` and add `GET /api/v1/games/{run_id}/state` that serializes `engine.game_state` directly when the run is live, falling back to disk reconstruction (`build_view`) for finished/evicted runs. The play loop and `serialize_game_state`/`role_data` widening are NOT touched here (M2/M3). We compose the `/state` shape (spec §5.1) in a new API-layer service from the existing `GameStateSnapshot` (live) and `ViewResponse` (disk).

Shared contract names from the spec this milestone must use verbatim: response keys `status`, `error`, `play_state`, `speed`, `phase`, `sub_phase`, `round`, `current_actor_seat`, `winner`, `sheriff_seat`, `alive_count`, `dead_count`, `last_night` (`deaths` `[{seat,cause}]`, `saved_seat`, `guarded_seat`, `poisoned_seat`), `votes` (`by_seat`, `tally`), `cursor`, `players` (`seat`, `name`, `role`, `camp`, `is_alive`, `is_sheriff`, `model`, `status_flags`). For M1 the live engine has no control gate yet, so `play_state` defaults to `"playing"` and `speed` to `1`; `sub_phase` and `current_actor_seat` are `null` (filled in M2/M3).

---

### Task 1 — Add `engine` field to `GameSession` and set it in `_run_game`

Files:
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_state_service.py`

Steps:

- [ ] Write the failing test asserting the dataclass has an `engine` field defaulting to `None`. Create `tests/interface/test_state_service.py` with:

```python
"""Unit tests for the /state composition service and engine wiring."""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.interface.api.services.game_sessions import GameSession


def _make_session(tmp_path: Path) -> GameSession:
    return GameSession(
        run_id="r1",
        run_dir=tmp_path,
        config_path=tmp_path / "cfg.yaml",
        config_id="demo-6",
    )


def test_game_session_has_engine_field_defaulting_none(tmp_path):
    session = _make_session(tmp_path)
    assert session.engine is None
```

- [ ] Run it and verify it FAILS (the dataclass has no `engine` field yet):

```
uv run pytest tests/interface/test_state_service.py::test_game_session_has_engine_field_defaulting_none -v
```

Expected: `FAILED ... AttributeError: 'GameSession' object has no attribute 'engine'`.

- [ ] Add the `engine` field to the `GameSession` dataclass. In `src/llm_werewolf/interface/api/services/game_sessions.py`, change:

```python
    human_seats: list[int] = field(default_factory=list)
```

to:

```python
    human_seats: list[int] = field(default_factory=list)
    engine: Any | None = None
```

- [ ] Run the test, verify it PASSES:

```
uv run pytest tests/interface/test_state_service.py::test_game_session_has_engine_field_defaulting_none -v
```

Expected: `1 passed`.

- [ ] Wire `session.engine` in `_run_game` so the live run retains its engine. In `src/llm_werewolf/interface/api/services/game_sessions.py`, change:

```python
            engine.setup_game(players=players, roles=roles)
            _write_full_roster(engine, session.run_dir)
```

to:

```python
            engine.setup_game(players=players, roles=roles)
            session.engine = engine
            _write_full_roster(engine, session.run_dir)
```

- [ ] Run the full game-sessions-related test module to confirm no regression from the dataclass/loop change:

```
uv run pytest tests/interface/test_api_actions.py -v
```

Expected: all existing tests still pass (e.g. `test_start_game_custom_roster PASSED`).

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_state_service.py && git commit -m "M1: retain live engine reference on GameSession"
```

---

### Task 2 — `/state` response models (`models/state.py`)

Files:
- Create: `src/llm_werewolf/interface/api/models/state.py`
- Test: `tests/interface/test_state_service.py`

Steps:

- [ ] Write the failing test for the model shape/defaults. Append to `tests/interface/test_state_service.py`:

```python
from llm_werewolf.interface.api.models.state import (
    GameStateResponse,
    LastNight,
    StatePlayer,
    StateVotes,
)


def test_state_models_defaults_match_spec():
    resp = GameStateResponse(status="running", phase="night", round=2)
    assert resp.play_state == "playing"
    assert resp.speed == 1
    assert resp.sub_phase is None
    assert resp.current_actor_seat is None
    assert resp.winner is None
    assert resp.error is None
    assert resp.last_night == LastNight()
    assert resp.votes == StateVotes()
    assert resp.players == []
    assert resp.cursor == 0


def test_state_player_status_flags_default_empty():
    p = StatePlayer(seat=1, name="P1")
    assert p.status_flags == []
    assert p.is_alive is True
    assert p.is_sheriff is False
```

- [ ] Run it and verify it FAILS (module does not exist):

```
uv run pytest tests/interface/test_state_service.py::test_state_models_defaults_match_spec -v
```

Expected: `FAILED ... ModuleNotFoundError: No module named 'llm_werewolf.interface.api.models.state'`.

- [ ] Create `src/llm_werewolf/interface/api/models/state.py` with the spec §5.1 shape:

```python
"""Authoritative live-state response models for GET /games/{run_id}/state (spec §5.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PlayState = Literal["playing", "paused"]
SessionStatus = Literal["running", "paused", "ended", "cancelled", "error"]
# sub_phase is an OPEN-ENDED display hint (spec §5.1 shows "... "). The engine's
# night scheduler (M3) emits free-form names beyond this canonical set (e.g.
# "pre_wolf", "werewolf_kill"), so the response field is `str | None` — this
# constant documents the common values but does NOT constrain the field.
COMMON_SUB_PHASES = (
    "werewolf_chat", "witch_decide", "seer_check", "guard", "graveyard_check",
)


class StatePlayer(BaseModel):
    seat: int
    name: str
    role: str | None = None
    camp: str | None = None
    is_alive: bool = True
    is_sheriff: bool = False
    model: str | None = None
    status_flags: list[str] = Field(default_factory=list)


class NightDeath(BaseModel):
    seat: int
    cause: str | None = None


class LastNight(BaseModel):
    deaths: list[NightDeath] = Field(default_factory=list)
    saved_seat: int | None = None
    guarded_seat: int | None = None
    poisoned_seat: int | None = None


class StateVotes(BaseModel):
    by_seat: dict[str, int] = Field(default_factory=dict)
    tally: dict[str, int] = Field(default_factory=dict)


class GameStateResponse(BaseModel):
    status: SessionStatus
    error: str | None = None
    play_state: PlayState = "playing"
    speed: int = 1
    phase: str = "setup"
    sub_phase: str | None = None    # open-ended display hint (see COMMON_SUB_PHASES)
    round: int = 0
    current_actor_seat: int | None = None
    winner: str | None = None
    sheriff_seat: int | None = None
    alive_count: int = 0
    dead_count: int = 0
    last_night: LastNight = Field(default_factory=LastNight)
    votes: StateVotes = Field(default_factory=StateVotes)
    cursor: int = 0
    players: list[StatePlayer] = Field(default_factory=list)
```

- [ ] Run the model tests, verify they PASS:

```
uv run pytest tests/interface/test_state_service.py::test_state_models_defaults_match_spec tests/interface/test_state_service.py::test_state_player_status_flags_default_empty -v
```

Expected: `2 passed`.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/models/state.py tests/interface/test_state_service.py && git commit -m "M1: add GameStateResponse models for /state (spec 5.1)"
```

---

### Task 3 — Compose `/state` from a live `GameStateSnapshot` (`build_state_from_snapshot`)

Files:
- Create: `src/llm_werewolf/interface/api/services/state.py`
- Test: `tests/interface/test_state_service.py`

Steps:

- [ ] Write the failing test that drives a `GameStateSnapshot` (from the real `serialize_game_state`) into `build_state_from_snapshot`. Append to `tests/interface/test_state_service.py`:

```python
from llm_werewolf.game_runtime.state.serialization import GameStateSnapshot, PlayerSnapshot
from llm_werewolf.interface.api.services.state import build_state_from_snapshot


def _snapshot() -> GameStateSnapshot:
    return GameStateSnapshot(
        players=[
            PlayerSnapshot(player_id="player_1", name="P1", role_name="Seer",
                           is_alive=True, statuses=["alive"], ai_model="deepseek-chat"),
            PlayerSnapshot(player_id="player_2", name="P2", role_name="Werewolf",
                           is_alive=False, statuses=["dead"], ai_model="doubao"),
            PlayerSnapshot(player_id="player_3", name="P3", role_name="Guard",
                           is_alive=True, statuses=["alive"], ai_model="demo"),
        ],
        phase="night",
        round_number=2,
        night_deaths=["player_2"],
        death_causes={"player_2": "wolf_kill"},
        witch_saved_target=None,
        witch_poison_target=None,
        guard_protected="player_3",
        votes={"player_1": "player_2", "player_3": "player_2"},
        sheriff_id="player_1",
        winner=None,
    )


def test_build_state_from_snapshot_authoritative_fields():
    state = build_state_from_snapshot(
        _snapshot(), status="running", error=None, cursor=142,
        camps={"player_1": "villager", "player_2": "werewolf", "player_3": "villager"},
    )
    assert state.status == "running"
    assert state.phase == "night"
    assert state.round == 2
    assert state.winner is None
    assert state.sheriff_seat == 1
    assert state.alive_count == 2
    assert state.dead_count == 1
    assert state.cursor == 142
    assert state.play_state == "playing"


def test_build_state_from_snapshot_last_night_and_votes():
    state = build_state_from_snapshot(
        _snapshot(), status="running", error=None, cursor=0, camps={},
    )
    assert [d.model_dump() for d in state.last_night.deaths] == [
        {"seat": 2, "cause": "wolf_kill"}
    ]
    assert state.last_night.guarded_seat == 3
    assert state.last_night.saved_seat is None
    assert state.votes.by_seat == {"1": 2, "3": 2}
    assert state.votes.tally == {"2": 2}


def test_build_state_from_snapshot_players_projection():
    state = build_state_from_snapshot(
        _snapshot(), status="running", error=None, cursor=0,
        camps={"player_1": "villager", "player_2": "werewolf"},
    )
    p1 = next(p for p in state.players if p.seat == 1)
    assert p1.role == "Seer"
    assert p1.camp == "villager"
    assert p1.is_sheriff is True
    assert p1.model == "deepseek-chat"
    assert p1.status_flags == ["alive"]
    p2 = next(p for p in state.players if p.seat == 2)
    assert p2.is_alive is False
    assert p2.is_sheriff is False
```

- [ ] Run it and verify it FAILS (module/function does not exist):

```
uv run pytest tests/interface/test_state_service.py -k build_state_from_snapshot -v
```

Expected: `FAILED ... ModuleNotFoundError: No module named 'llm_werewolf.interface.api.services.state'`.

- [ ] Create `src/llm_werewolf/interface/api/services/state.py` with the live composer (seat parsing mirrors `_seat_of` in `services/view.py` and `_write_full_roster`):

```python
"""Compose the authoritative GET /state response (spec §5.1).

Live path: from a GameStateSnapshot produced by serialize_game_state.
Disk fallback path: from a ViewResponse produced by build_view.
"""

from __future__ import annotations

from llm_werewolf.game_runtime.state.serialization import GameStateSnapshot
from llm_werewolf.interface.api.models.state import (
    GameStateResponse,
    LastNight,
    NightDeath,
    StatePlayer,
    StateVotes,
)
from llm_werewolf.interface.api.models.view import ViewResponse


def _seat_of(player_id: str | None) -> int | None:
    if not player_id:
        return None
    try:
        return int(str(player_id).rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return None


def _last_night(snapshot: GameStateSnapshot) -> LastNight:
    deaths = [
        NightDeath(seat=seat, cause=snapshot.death_causes.get(pid))
        for pid in snapshot.night_deaths
        if (seat := _seat_of(pid)) is not None
    ]
    deaths.sort(key=lambda d: d.seat)
    return LastNight(
        deaths=deaths,
        saved_seat=_seat_of(snapshot.witch_saved_target),
        guarded_seat=_seat_of(snapshot.guard_protected),
        poisoned_seat=_seat_of(snapshot.witch_poison_target),
    )


def _votes(snapshot: GameStateSnapshot) -> StateVotes:
    by_seat: dict[str, int] = {}
    tally: dict[str, int] = {}
    for voter_id, target_id in snapshot.votes.items():
        voter_seat = _seat_of(voter_id)
        target_seat = _seat_of(target_id)
        if voter_seat is None or target_seat is None:
            continue
        by_seat[str(voter_seat)] = target_seat
        tally[str(target_seat)] = tally.get(str(target_seat), 0) + 1
    return StateVotes(by_seat=by_seat, tally=tally)


def build_state_from_snapshot(
    snapshot: GameStateSnapshot,
    *,
    status: str,
    error: str | None,
    cursor: int,
    camps: dict[str, str],
) -> GameStateResponse:
    sheriff_seat = _seat_of(snapshot.sheriff_id)
    players: list[StatePlayer] = []
    alive_count = 0
    for p in snapshot.players:
        seat = _seat_of(p.player_id)
        if seat is None:
            continue
        if p.is_alive:
            alive_count += 1
        players.append(StatePlayer(
            seat=seat,
            name=p.name,
            role=p.role_name,
            camp=camps.get(p.player_id),
            is_alive=p.is_alive,
            is_sheriff=(seat == sheriff_seat),
            model=p.ai_model,
            status_flags=list(p.statuses),
        ))
    players.sort(key=lambda sp: sp.seat)
    return GameStateResponse(
        status=status,
        error=error,
        phase=snapshot.phase,
        round=snapshot.round_number,
        winner=snapshot.winner,
        sheriff_seat=sheriff_seat,
        alive_count=alive_count,
        dead_count=len(players) - alive_count,
        last_night=_last_night(snapshot),
        votes=_votes(snapshot),
        cursor=cursor,
        players=players,
    )
```

- [ ] Run the live-composer tests, verify they PASS:

```
uv run pytest tests/interface/test_state_service.py -k build_state_from_snapshot -v
```

Expected: `3 passed`.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/state.py tests/interface/test_state_service.py && git commit -m "M1: compose /state from live GameStateSnapshot"
```

---

### Task 4 — Disk-fallback composer (`build_state_from_view`)

Files:
- Modify: `src/llm_werewolf/interface/api/services/state.py`
- Test: `tests/interface/test_state_service.py`

Steps:

- [ ] Write the failing test that drives a real `build_view` output through `build_state_from_view`. Append to `tests/interface/test_state_service.py`:

```python
import json

from llm_werewolf.interface.api.services.state import build_state_from_view
from llm_werewolf.interface.api.services.view import build_view


def _seed_finished_run(tmp_path) -> Path:
    run_dir = tmp_path / "finished"
    run_dir.mkdir()
    (run_dir / "roster.json").write_text(json.dumps({"players": [
        {"seat": 1, "player_id": "player_1", "name": "P1", "role": "预言家",
         "camp": "villager", "model": "deepseek-chat"},
        {"seat": 2, "player_id": "player_2", "name": "P2", "role": "狼人",
         "camp": "werewolf", "model": "doubao"},
    ]}), encoding="utf-8")
    rows = [
        {"event_type": "sheriff_elected", "round_number": 1, "phase": "sheriff_election",
         "message": "1号当选警长", "data": {"player_id": "player_1"}},
        {"event_type": "player_eliminated", "round_number": 1, "phase": "day_voting",
         "message": "2号被放逐", "data": {"player_id": "player_2", "player_name": "P2"}},
        {"event_type": "game_ended", "round_number": 1, "phase": "ended",
         "message": "好人获胜", "data": {"winner_camp": "villager"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return run_dir


def test_build_state_from_view_disk_fallback(tmp_path):
    run_dir = _seed_finished_run(tmp_path)
    view = build_view(run_dir, since=0, status="ended", error=None)
    state = build_state_from_view(view)
    assert state.status == "ended"
    assert state.phase == "ended"
    assert state.round == 1
    assert state.winner == "villager"
    assert state.sheriff_seat == 1
    assert state.alive_count == 1
    assert state.dead_count == 1
    assert state.cursor == 3
    p1 = next(p for p in state.players if p.seat == 1)
    assert p1.role == "预言家"
    assert p1.camp == "villager"
    assert p1.is_sheriff is True
    p2 = next(p for p in state.players if p.seat == 2)
    assert p2.is_alive is False
    assert p2.status_flags == ["dead"]
```

- [ ] Run it and verify it FAILS (function does not exist):

```
uv run pytest tests/interface/test_state_service.py::test_build_state_from_view_disk_fallback -v
```

Expected: `FAILED ... ImportError: cannot import name 'build_state_from_view'`.

- [ ] Add `build_state_from_view` to `src/llm_werewolf/interface/api/services/state.py`. Append:

```python
def build_state_from_view(view: ViewResponse) -> GameStateResponse:
    snap = view.snapshot
    tally: dict[str, int] = {}
    if isinstance(snap.vote_tally, dict):
        for target, count in snap.vote_tally.items():
            try:
                tally[str(target)] = int(count)
            except (TypeError, ValueError):
                continue
    players = [
        StatePlayer(
            seat=p.seat,
            name=p.name,
            role=p.role,
            camp=p.camp,
            is_alive=p.is_alive,
            is_sheriff=p.is_sheriff,
            model=p.model,
            status_flags=["alive"] if p.is_alive else ["dead"],
        )
        for p in snap.players
    ]
    players.sort(key=lambda sp: sp.seat)
    return GameStateResponse(
        status=view.status,
        error=view.error,
        phase=snap.phase,
        round=snap.day,
        winner=snap.winner,
        sheriff_seat=snap.sheriff_seat,
        alive_count=snap.alive_count,
        dead_count=snap.dead_count,
        votes=StateVotes(tally=tally),
        cursor=view.cursor,
        players=players,
    )
```

- [ ] Add the `ViewResponse` import already present at top of file (confirm the import line `from llm_werewolf.interface.api.models.view import ViewResponse` exists from Task 3; it does). Run the disk-fallback test, verify it PASSES:

```
uv run pytest tests/interface/test_state_service.py::test_build_state_from_view_disk_fallback -v
```

Expected: `1 passed`.

- [ ] Run the full state-service module to confirm both composers are green together:

```
uv run pytest tests/interface/test_state_service.py -v
```

Expected: all tests pass.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/state.py tests/interface/test_state_service.py && git commit -m "M1: disk-fallback /state composer from build_view"
```

---

### Task 5 — `GameSessionManager.get_state` (live-vs-disk picker)

Files:
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_state_service.py`

Steps:

- [ ] Write the failing test for the picker: live engine present → live snapshot; no session / no engine → disk fallback; unknown run → None. Append to `tests/interface/test_state_service.py`:

```python
from types import SimpleNamespace

from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.interface.api.services.game_sessions import (
    GameSessionManager,
    GameSessionStatus,
)


def _live_engine():
    role = SimpleNamespace(camp=SimpleNamespace(value="villager"))
    player = SimpleNamespace(
        player_id="player_1", name="P1", ai_model="deepseek-chat",
        get_role_name=lambda: "Seer", get_camp=lambda: role.camp,
        is_alive=lambda: True, statuses=[SimpleNamespace(value="alive")],
        lover_partner_id=None, can_vote_flag=True, role=role,
    )
    game_state = SimpleNamespace(
        players=[player], phase=GamePhase.NIGHT, round_number=2,
        night_deaths=set(), day_deaths=set(), death_abilities_used=set(),
        death_causes={}, werewolf_target=None, werewolf_votes={},
        witch_save_used=False, witch_poison_used=False, witch_saved_target=None,
        witch_poison_target=None, guard_protected=None, guardian_wolf_protected=None,
        nightmare_blocked=None, seer_checked={}, graveyard_checked={}, votes={},
        raven_marked=None, wolf_beauty_charmed=None, sheriff_id=None,
        enable_sheriff=False, sheriff_election_done=False, sheriff_votes={},
        sheriff_tie_count=0, vote_tie_count=0, winner=None,
    )
    return SimpleNamespace(game_state=game_state)


def test_get_state_uses_live_engine(tmp_path):
    mgr = GameSessionManager()
    session = GameSession(
        run_id="live-1", run_dir=tmp_path, config_path=tmp_path / "c.yaml",
        config_id="demo-6", status=GameSessionStatus.RUNNING,
    )
    session.engine = _live_engine()
    mgr._sessions["live-1"] = session
    state = mgr.get_state("live-1", runs_dir=tmp_path, eval_runs_dir=tmp_path)
    assert state is not None
    assert state.status == "running"
    assert state.phase == "night"
    assert state.round == 2
    assert state.players[0].camp == "villager"


def test_get_state_disk_fallback_when_no_session(tmp_path):
    run_dir = _seed_finished_run(tmp_path)
    runs_dir = run_dir.parent
    mgr = GameSessionManager()
    state = mgr.get_state("finished", runs_dir=runs_dir, eval_runs_dir=runs_dir)
    assert state is not None
    assert state.status == "ended"
    assert state.winner == "villager"


def test_get_state_unknown_run_returns_none(tmp_path):
    mgr = GameSessionManager()
    state = mgr.get_state("nope", runs_dir=tmp_path, eval_runs_dir=tmp_path)
    assert state is None
```

- [ ] Run it and verify it FAILS (no `get_state` method):

```
uv run pytest tests/interface/test_state_service.py -k get_state -v
```

Expected: `FAILED ... AttributeError: 'GameSessionManager' object has no attribute 'get_state'`.

- [ ] Add the `get_state` method to `GameSessionManager` in `src/llm_werewolf/interface/api/services/game_sessions.py`, immediately after `get_view`. Insert:

```python
    def get_state(
        self, run_id: str, *, runs_dir: Path, eval_runs_dir: Path,
        source: str | None = None,
    ) -> "GameStateResponse | None":
        from llm_werewolf.game_runtime.state.serialization import serialize_game_state
        from llm_werewolf.interface.api.services.state import (
            build_state_from_snapshot,
            build_state_from_view,
        )
        from llm_werewolf.interface.api.services.view import build_view

        status_map = {
            GameSessionStatus.RUNNING: "running", GameSessionStatus.PENDING: "running",
            GameSessionStatus.COMPLETED: "ended", GameSessionStatus.CANCELLED: "cancelled",
            GameSessionStatus.FAILED: "error",
        }

        session = self._sessions.get(run_id)
        if session is not None and session.engine is not None:
            engine = session.engine
            game_state = getattr(engine, "game_state", None)
            if game_state is not None:
                snapshot = serialize_game_state(game_state)
                camps = {
                    p.player_id: p.get_camp().value
                    for p in game_state.players
                    if getattr(p, "role", None) is not None
                }
                cursor = self._count_events(session.run_dir)
                return build_state_from_snapshot(
                    snapshot,
                    status=status_map.get(session.status, "running"),
                    error=session.error,
                    cursor=cursor,
                    camps=camps,
                )

        if session is not None:
            run_dir = session.run_dir
            status = status_map.get(session.status, "running")
            error = session.error
        else:
            detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
            if detail is None:
                return None
            run_dir = Path(detail.path)
            status, error = "ended", None
        if not run_dir.is_dir():
            return None
        view = build_view(run_dir, since=0, status=status, error=error)
        return build_state_from_view(view)

    @staticmethod
    def _count_events(run_dir: Path) -> int:
        path = run_dir / "events.jsonl"
        if not path.is_file():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
```

- [ ] Add the `GameStateResponse` forward-ref import to the `TYPE_CHECKING` block at the top of the file so the return annotation resolves. Change:

```python
if TYPE_CHECKING:
    from llm_werewolf.interface.api.models.view import ViewResponse
```

to:

```python
if TYPE_CHECKING:
    from llm_werewolf.interface.api.models.state import GameStateResponse
    from llm_werewolf.interface.api.models.view import ViewResponse
```

- [ ] Run the picker tests, verify they PASS:

```
uv run pytest tests/interface/test_state_service.py -k get_state -v
```

Expected: `3 passed`.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_state_service.py && git commit -m "M1: GameSessionManager.get_state live-vs-disk picker"
```

---

### Task 6 — `GET /api/v1/games/{run_id}/state` route

Files:
- Modify: `src/llm_werewolf/interface/api/routes/actions.py`
- Test: `tests/interface/test_api_state.py`

Steps:

- [ ] Write the failing route tests. Create `tests/interface/test_api_state.py`:

```python
"""Route tests for GET /api/v1/games/{run_id}/state."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_state_disk_fallback_for_sample_run(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/games/test-run-1/state", params={"source": "runs"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "ended"
    assert data["phase"] == "ended"
    assert data["winner"] == "werewolf"
    assert data["play_state"] == "playing"
    assert data["speed"] == 1
    assert isinstance(data["players"], list)
    assert data["last_night"] == {
        "deaths": [], "saved_seat": None, "guarded_seat": None, "poisoned_seat": None,
    }


def test_state_missing_run_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/games/no-such-run/state")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Run not found: no-such-run"
```

- [ ] Run it and verify it FAILS (route not registered → 404 on the sample run too):

```
uv run pytest tests/interface/test_api_state.py::test_state_disk_fallback_for_sample_run -v
```

Expected: `FAILED ... assert 404 == 200`.

- [ ] Add the route and model import to `src/llm_werewolf/interface/api/routes/actions.py`. Extend the model import block — change:

```python
from llm_werewolf.interface.api.models.actions import (
    ActionSpecResponse,
    CancelGameResponse,
    GameStatusResponse,
    ModelCompareRequest,
    ModelCompareResponse,
    PageActionSpec,
    StartGameModesResponse,
    StartGameRequest,
    StartGameResponse,
    TriggerPostGameRequest,
    TriggerPostGameResponse,
)
```

to:

```python
from llm_werewolf.interface.api.models.actions import (
    ActionSpecResponse,
    CancelGameResponse,
    GameStatusResponse,
    ModelCompareRequest,
    ModelCompareResponse,
    PageActionSpec,
    StartGameModesResponse,
    StartGameRequest,
    StartGameResponse,
    TriggerPostGameRequest,
    TriggerPostGameResponse,
)
from llm_werewolf.interface.api.models.state import GameStateResponse
```

Then add the route directly after the existing `game_view` route:

```python
@router.get("/games/{run_id}/state")
def game_state_snapshot(
    run_id: str,
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[GameStateResponse]:
    data = game_session_manager.get_state(
        run_id, runs_dir=runs_dir, eval_runs_dir=eval_runs_dir, source=source,
    )
    if data is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ApiResponse(data=data)
```

- [ ] Run the route tests, verify they PASS:

```
uv run pytest tests/interface/test_api_state.py -v
```

Expected: `2 passed`.

- [ ] Add a `PageActionSpec` entry so the `/actions/spec` catalog advertises the new endpoint (matches existing convention for `poll_status`). In `src/llm_werewolf/interface/api/routes/actions.py`, inside `ACTION_SPECS`, add after the `poll_status` spec:

```python
    PageActionSpec(
        page_key="game",
        frontend_route="/game",
        action="get_state",
        method="GET",
        api_path="/api/v1/games/{run_id}/state",
        description="Authoritative live game state snapshot",
        response_model="GameStateResponse",
    ),
```

- [ ] Run the actions-spec regression test, verify it still PASSES:

```
uv run pytest tests/interface/test_api_actions.py::test_actions_spec -v
```

Expected: `1 passed`.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/routes/actions.py tests/interface/test_api_state.py && git commit -m "M1: add GET /games/{run_id}/state route + action spec"
```

---

### Task 7 — Full-suite regression guard for M1

Files:
- (no new files; verification only)

Steps:

- [ ] Run the entire interface test package to confirm no regressions from the dataclass/loop/route changes:

```
uv run pytest tests/interface -v
```

Expected: all interface tests pass (existing `test_api_actions.py`, `test_view_service.py`, `test_api_services.py`, plus the new `test_state_service.py` and `test_api_state.py`).

- [ ] Run the serialization tests to confirm `serialize_game_state` was not disturbed (we only consume it):

```
uv run pytest tests/ -k serialization -v
```

Expected: all matching tests pass.

- [ ] Commit any incidental formatting (none expected); if clean, record the green state:

```
git add -A && git commit -m "M1: green full interface suite for engine-retained /state" --allow-empty
```

---

## M2 — Step-pump loop + control gate (pause/resume/step/speed) + last_night capture + step() reconciliation

**Coverage:** Covers spec section 6 items 2 (step-pump loop), 3 (reconcile step() with play_game(): reset_deaths at NIGHT, remove SETUP placeholders, single check_victory/GAME_ENDED) and 4 (capture night results before next_phase() clears them, surface as last_night); spec section 5.3 (POST /control pause|resume|step|speed) and the parts of 5.1 that depend on this milestone (status collapses to "paused" for a paused running game per §5.1, play_state, speed, last_night as a typed LastNight model). Implements the section 9 tests: step()==play_game() equivalence with single GAME_ENDED, last_night capture, and control-gate behavior (pause/step/resume/speed). Phase-signal emission (item 5), sub_phase events (item 6), the five typed skill events (item 7) and EventHub/SSE (items 8-9) are explicitly OUT of scope here (M3/M4). M2 assumes M1 already added GameSession.engine and GET /state.

**File structure:**

| File | Action | Responsibility |
|---|---|---|
| `src/llm_werewolf/game_runtime/engine/base.py` | modify | Add is_over() helper; reconcile step() with play_game() (reset_deaths at NIGHT entry, drop SETUP placeholder strings, advance SETUP silently, ensure check_victory fires at the same boundaries exactly once). |
| `src/llm_werewolf/interface/api/services/game_sessions.py` | modify | Add control-gate fields + last_night capture fields to GameSession; add capture_phase_snapshot(); replace 'await engine.play_game()' in _run_game with the step-pump loop honoring gate/step_once/speed; add GameSessionManager.control(); in get_state's live branch derive play_state/speed/status-collapse-to-paused and convert the captured last_night dict to a typed LastNight (Task 6) — does NOT touch any model file. |
| `src/llm_werewolf/interface/api/services/state.py` | modify | Task 6: add captured_last_night/play_state/speed override params to build_state_from_snapshot so the live /state surfaces the gate state + captured night results (no model change). |
| `src/llm_werewolf/interface/api/models/actions.py` | modify | Add ControlGameRequest (action enum + optional value) and ControlGameResponse (run_id, play_state, speed, phase) schemas. (NOT GameStateResponse — that lives in M1's models/state.py.) |
| `src/llm_werewolf/interface/api/routes/actions.py` | modify | Add POST /games/{run_id}/control route wired to GameSessionManager.control(). |
| `tests/game_runtime/test_engine_step_equivalence.py` | create | Seeded DemoAgent game: assert step()-pump produces identical final phase/winner/deaths and the same PHASE_CHANGED+GAME_ENDED event sequence as play_game(), with exactly one GAME_ENDED; assert reset_deaths at NIGHT entry and no SETUP placeholder strings. |
| `tests/interface/test_api_control.py` | create | Tests for capture_phase_snapshot/last_night, the step-pump loop (pause halts after current phase, step advances one phase, resume continues, speed sets dwell factor) and the POST /control endpoint (404 for unknown run, response shape). |

> **Depends on M1**: this milestone assumes M1 already (a) added a live `engine` reference to `GameSession` (set in `_run_game` before the run loop) and (b) shipped `GET /api/v1/games/{run_id}/state` backed by `serialize_game_state(engine.game_state)`. M2 populates the already-declared `/state` fields at runtime (collapses `play_state` from the gate, exposes `speed`, attaches the captured typed `last_night`, and collapses `status` to "paused" for a paused running game) and replaces the `await engine.play_game()` call. M2 does **not** redefine any `GameStateResponse` field — those live solely in M1's `models/state.py`. If M1 has not landed when you start, do **Task 1**'s `session.engine = engine` assignment as part of Task 4 (noted inline) so M2 is self-contained.

The highest-risk change is `step()` reconciliation (game-logic equivalence). Per the spec we do that **first**, behind the equivalence test, before anything depends on it.

---

### Task 1 — Add `is_over()` and reconcile `engine.step()` with `play_game()`

**Files**
- Modify: `src/llm_werewolf/game_runtime/engine/base.py`
- Test: `tests/game_runtime/test_engine_step_equivalence.py` (create)

The known divergences (read from the current source):
- `play_game()` calls `self.game_state.reset_deaths()` at the **top of every loop** (i.e. before each NIGHT). `step()` at `GamePhase.NIGHT` does **not** call `reset_deaths()`.
- `step()` at `GamePhase.SETUP` emits placeholder strings `"Game initialized! Press 'n' to start the first night phase."` / `f"Round {round} begins."`; `play_game()` advances `SETUP→NIGHT` silently (via `next_phase()` inside the first `run_night_phase()` which itself calls `set_phase(NIGHT)`).
- Both paths funnel `phase=ENDED`, `winner`, and the single `GAME_ENDED` event through `check_victory()`. We must keep that the only place those side effects happen, and ensure it fires at equivalent boundaries exactly once.

- [ ] **Write the failing equivalence test.** Create `tests/game_runtime/test_engine_step_equivalence.py`:
  ```python
  """step()-pump must be behavior-equivalent to play_game()."""

  from __future__ import annotations

  import random

  import pytest

  from llm_werewolf.agent_team.agents.base import DemoAgent
  from llm_werewolf.game_runtime import GameEngine
  from llm_werewolf.game_runtime.config import create_game_config_from_player_count
  from llm_werewolf.game_runtime.roles.registry import create_roles
  from llm_werewolf.game_runtime.types import EventType, GamePhase


  def _build_engine(seed: int) -> GameEngine:
      random.seed(seed)
      config = create_game_config_from_player_count(6)
      engine = GameEngine(config)
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
  ```

- [ ] **Run each red test separately so the failure mode is unambiguous** (`is_over` does not exist yet and `step()` still emits SETUP placeholders / skips `reset_deaths`). Run them one at a time, each with its own distinct expected failure:

  1. The equivalence test fails first on the missing `is_over()` helper:
  ```
  uv run pytest tests/game_runtime/test_engine_step_equivalence.py::test_step_pump_matches_play_game -v
  ```
  Expected: `FAILED ... AttributeError: 'GameEngine' object has no attribute 'is_over'`.

  2. The SETUP test fails on the placeholder strings still emitted by `step()` at SETUP:
  ```
  uv run pytest tests/game_runtime/test_engine_step_equivalence.py::test_step_setup_advances_to_night_without_placeholders -v
  ```
  Expected: `FAILED ... assert "Press 'n'" not in joined` (the SETUP branch still appends `"Game initialized! ..."` / `"... Press 'n' ..."`).

  3. The deaths test fails because NIGHT entry does not call `reset_deaths()`:
  ```
  uv run pytest tests/game_runtime/test_engine_step_equivalence.py::test_step_resets_deaths_at_night_entry -v
  ```
  Expected: `FAILED ... assert "stale_player" not in engine.game_state.night_deaths` (the stale death is not cleared at NIGHT entry).

- [ ] **Add `is_over()` to `GameEngineBase`.** Insert directly after `check_victory()` (after `base.py:285`):
  ```python
      def is_over(self) -> bool:
          """游戏是否已结束（阶段为 ENDED）。"""
          if not self.game_state:
              return False
          return self.game_state.get_phase() == GamePhase.ENDED
  ```

- [ ] **Reconcile `step()` SETUP + NIGHT branches.** Replace the SETUP and NIGHT branches inside `step()` (`base.py:578-591`) so SETUP advances silently and NIGHT resets deaths first:
  ```python
          if current_phase == GamePhase.SETUP:
              self.game_state.next_phase()
              phase_messages = []
          elif current_phase == GamePhase.NIGHT:
              self.game_state.reset_deaths()
              phase_messages = await self.run_night_phase()
              if not self.check_victory():
                  self.game_state.next_phase()
                  if self.game_state.get_phase() == GamePhase.SHERIFF_ELECTION:
                      await self.execute_sheriff_election()
                      self.game_state.next_phase()
  ```
  (We drop the two placeholder strings and the trailing `"Sheriff election completed."` append; the sheriff election is now silent here, matching `play_game()` which appends no message.)

- [ ] **Reconcile the SHERIFF_ELECTION / DAY_VOTING branches' messages.** Replace the standalone SHERIFF_ELECTION branch (`base.py:592-595`) to drop its placeholder message so it matches `play_game()`:
  ```python
          elif current_phase == GamePhase.SHERIFF_ELECTION:
              await self.execute_sheriff_election()
              self.game_state.next_phase()
              phase_messages = []
  ```

- [ ] **Run the test, verify it PASSES.**
  ```
  uv run pytest tests/game_runtime/test_engine_step_equivalence.py -v
  ```
  Expected: all four tests PASS — the step-pump reaches the same final phase/winner/deaths, the PHASE_CHANGED+GAME_ENDED signature matches, GAME_ENDED appears exactly once on each path, SETUP emits no placeholder strings, and NIGHT entry clears stale deaths.

- [ ] **Run the regression guard for `step()` memory hooks** (it monkeypatches `check_victory` and asserts `on_round_end` once — our DAY_VOTING branch is unchanged so it must still pass):
  ```
  uv run pytest tests/game_runtime/test_memory_round_hooks.py -v
  ```
  Expected: `test_step_day_voting_triggers_memory_round_end PASSED`.

- [ ] **Commit.**
  ```
  git add src/llm_werewolf/game_runtime/engine/base.py tests/game_runtime/test_engine_step_equivalence.py && git commit -m "Reconcile engine.step() with play_game() and add is_over()

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

### Task 2 — Add control-gate state + `last_night` capture to `GameSession`

**Files**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_api_control.py` (create)

`GameSession` is a `@dataclass`. We add the live control gate (`asyncio.Event`), the `step_once` flag, an integer `speed` (1|2|4), an `engine` reference (M1 already adds this; declare it here if M1 has not landed), and a `last_night` dict captured between phases. `capture_phase_snapshot()` reads the night-result fields **before** `next_phase()` clears them.

- [ ] **Write the failing test for `capture_phase_snapshot`.** Create `tests/interface/test_api_control.py`:
  ```python
  """Step-pump control gate + last_night capture + /control endpoint."""

  from __future__ import annotations

  import asyncio
  from pathlib import Path

  import pytest

  from llm_werewolf.agent_team.agents.base import DemoAgent
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
      engine = GameEngine(config)
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
  ```

- [ ] **Run it, verify it FAILS.**
  ```
  uv run pytest tests/interface/test_api_control.py -v
  ```
  Expected: `AttributeError: 'GameSession' object has no attribute 'gate'`.

- [ ] **Add a seat helper + extend `GameSession`.** In `game_sessions.py`, add a module-level helper near `_write_full_roster` (after `_write_full_roster`, around `:81`):
  ```python
  def _seat_of(player_id: str) -> int | None:
      """Parse the 1-based seat number out of a 'player_N' id."""
      try:
          return int(player_id.rsplit("_", 1)[-1])
      except (ValueError, AttributeError):
          return None
  ```
  Then add the control-gate + capture fields to the `GameSession` dataclass (after the `engine` field added in M1 Task 1 — do NOT re-declare `engine`):
  ```python
      gate: asyncio.Event = field(default_factory=lambda: _playing_event())
      step_once: bool = False
      speed: int = 1
      last_night: dict[str, Any] = field(default_factory=dict)
  ```
  And add the gate factory above the `GameSession` class (before `:99`, after `_dump_roster_without_secrets`):
  ```python
  def _playing_event() -> asyncio.Event:
      """Control gate that starts in the 'playing' (set) state."""
      ev = asyncio.Event()
      ev.set()
      return ev
  ```

- [ ] **Implement `capture_phase_snapshot`.** Add the method to the `GameSession` dataclass body (after the field block):
  ```python
      def capture_phase_snapshot(self) -> None:
          """Snapshot night results BEFORE next_phase()/reset_deaths() clears them."""
          engine = self.engine
          state = getattr(engine, "game_state", None) if engine else None
          if state is None:
              return
          if state.get_phase() != GamePhase.NIGHT:
              return
          deaths = [
              {"seat": _seat_of(pid), "cause": state.death_causes.get(pid, "unknown")}
              for pid in sorted(state.night_deaths)
          ]
          self.last_night = {
              "deaths": [d for d in deaths if d["seat"] is not None],
              "saved_seat": _seat_of(state.witch_saved_target) if state.witch_saved_target else None,
              "guarded_seat": _seat_of(state.guard_protected) if state.guard_protected else None,
              "poisoned_seat": _seat_of(state.witch_poison_target) if state.witch_poison_target else None,
          }
  ```
  Add the import at the top of the file (next to the other `game_runtime` imports, around `:18`):
  ```python
  from llm_werewolf.game_runtime.types import GamePhase
  ```

- [ ] **Run the test, verify it PASSES.**
  ```
  uv run pytest tests/interface/test_api_control.py -v
  ```
  Expected: `test_session_defaults_playing_speed_one`, `test_capture_phase_snapshot_records_night_results`, and `test_capture_phase_snapshot_survives_next_phase_clear` all PASS.

- [ ] **Commit.**
  ```
  git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_control.py && git commit -m "Add control-gate state and last_night capture to GameSession

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

### Task 3 — Replace `play_game()` with the step-pump loop in `_run_game`

**Files**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_api_control.py` (extend)

We replace `result = await engine.play_game()` with a loop that awaits the gate between phases, runs one `engine.step()`, captures the night snapshot before the next phase clears it, auto-pauses on single-step, and applies an inter-phase dwell scaled by `speed`. The loop produces the same `result_text` `play_game()` returned.

- [ ] **Write the failing step-pump test.** Append to `tests/interface/test_api_control.py`:
  ```python
  @pytest.mark.asyncio
  async def test_run_step_pump_completes_game(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
      import random
      from llm_werewolf.interface.api.services.game_sessions import GameSessionManager

      random.seed(99)
      session = _session(tmp_path)
      engine = GameEngine(create_game_config_from_player_count(6))
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
      engine = GameEngine(create_game_config_from_player_count(6))
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
  ```

- [ ] **Run it, verify it FAILS.**
  ```
  uv run pytest tests/interface/test_api_control.py::test_run_step_pump_completes_game tests/interface/test_api_control.py::test_step_pump_pause_halts_after_current_phase tests/interface/test_api_control.py::test_step_pump_single_step_runs_one_phase -v
  ```
  Expected: `AttributeError: type object 'GameSessionManager' has no attribute '_run_step_pump'`.

- [ ] **Implement `_run_step_pump` as a staticmethod on `GameSessionManager`.** Add it directly above `_run_game` (before `:234`):
  ```python
      @staticmethod
      async def _run_step_pump(session: GameSession, *, dwell: float = 0.4) -> str:
          """Pump engine.step() one phase at a time, honoring the control gate."""
          engine = session.engine
          while not engine.is_over():
              await session.gate.wait()                 # honor pause/step
              await engine.step()                       # one phase
              session.capture_phase_snapshot()          # snapshot BEFORE next clear
              if session.step_once:
                  session.step_once = False
                  session.gate.clear()
              if dwell:
                  await asyncio.sleep(dwell / max(session.speed, 1))
          if engine.game_state and engine.game_state.winner:
              return engine.locale.get("game_over", winner=engine.game_state.winner)
          return engine.locale.get("game_ended", winner="unknown", reason="")
  ```

- [ ] **Wire it into `_run_game`.** In `_run_game`, replace the single line `result = await engine.play_game()` (`:251`) with:
  ```python
              session.engine = engine
              result = await self._run_step_pump(session)
  ```
  (The `session.engine = engine` assignment is M1's plumbing; keep it here even if M1 already sets it — re-assigning the same object is harmless and keeps M2 runnable standalone.)

- [ ] **Run the new tests, verify they PASS.**
  ```
  uv run pytest tests/interface/test_api_control.py::test_run_step_pump_completes_game tests/interface/test_api_control.py::test_step_pump_pause_halts_after_current_phase tests/interface/test_api_control.py::test_step_pump_single_step_runs_one_phase -v
  ```
  Expected: all three PASS — the pump drives the game to `ENDED` with one GAME_ENDED, pause blocks before any phase runs, and single-step runs exactly one phase then auto-clears the gate.

- [ ] **Run the existing session-manager API tests to confirm no regression** (start_game patches `_run_game`, so the pump is not invoked there, but verify the module still imports and behaves):
  ```
  uv run pytest tests/interface/test_api_actions.py -v
  ```
  Expected: all existing action tests still PASS.

- [ ] **Commit.**
  ```
  git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_control.py && git commit -m "Replace play_game() with step-pump loop honoring control gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

### Task 4 — Control request/response models + `GameSessionManager.control()`

**Files**
- Modify: `src/llm_werewolf/interface/api/models/actions.py`
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_api_control.py` (extend)

`control()` mutates the live gate/flags and returns the current `play_state`/`speed`/`phase`. Actions: `pause` clears the gate; `resume` sets it; `step` sets `step_once=True` then sets the gate (the pump runs one phase then auto-clears); `speed` validates `value ∈ {1,2,4}` and stores it.

- [ ] **Write the failing `control()` test.** Append to `tests/interface/test_api_control.py`:
  ```python
  @pytest.mark.asyncio
  async def test_control_pause_resume_step_speed(tmp_path: Path) -> None:
      from llm_werewolf.interface.api.services.game_sessions import (
          GameSessionManager,
          GameSessionStatus,
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
  ```

- [ ] **Run it, verify it FAILS.**
  ```
  uv run pytest tests/interface/test_api_control.py::test_control_pause_resume_step_speed -v
  ```
  Expected: `AttributeError: 'GameSessionManager' object has no attribute 'control'`.

- [ ] **Add the request/response schemas.** In `src/llm_werewolf/interface/api/models/actions.py`, after `CancelGameResponse` (`:127`):
  ```python
  class ControlGameRequest(BaseModel):
      action: str = Field(..., pattern="^(pause|resume|step|speed)$")
      value: int | None = Field(default=None, description="Speed factor; required for action=speed")

      @field_validator("value")
      @classmethod
      def validate_value(cls, value: int | None) -> int | None:
          if value is not None and value not in (1, 2, 4):
              msg = f"speed value must be one of 1, 2, 4; got {value}"
              raise ValueError(msg)
          return value


  class ControlGameResponse(BaseModel):
      run_id: str
      play_state: str
      speed: int
      phase: str
  ```

- [ ] **Implement `control()` on `GameSessionManager`.** Add it after `cancel_game` (after `:385`):
  ```python
      async def control(
          self, run_id: str, *, action: str, value: int | None = None
      ) -> ControlGameResponse | None:
          session = self._sessions.get(run_id)
          if session is None:
              return None
          if action == "pause":
              session.gate.clear()
          elif action == "resume":
              session.gate.set()
          elif action == "step":
              session.step_once = True
              session.gate.set()
          elif action == "speed":
              if value not in (1, 2, 4):
                  msg = f"speed value must be one of 1, 2, 4; got {value}"
                  raise ValueError(msg)
              session.speed = value
          state = getattr(session.engine, "game_state", None)
          phase = state.get_phase().value if state else GamePhase.SETUP.value
          return ControlGameResponse(
              run_id=run_id,
              play_state="playing" if session.gate.is_set() else "paused",
              speed=session.speed,
              phase=phase,
          )
  ```
  Add `ControlGameRequest, ControlGameResponse` to the existing `from llm_werewolf.interface.api.models.actions import (...)` block at the top of `game_sessions.py` (`:21-27`).

- [ ] **Run the tests, verify they PASS.**
  ```
  uv run pytest tests/interface/test_api_control.py::test_control_pause_resume_step_speed tests/interface/test_api_control.py::test_control_unknown_run_returns_none tests/interface/test_api_control.py::test_control_rejects_bad_speed -v
  ```
  Expected: all three PASS — pause/resume toggle the gate, step sets `step_once` and re-arms the gate, speed=4 is stored, unknown run returns `None`, and speed=3 raises `ValueError`.

- [ ] **Commit.**
  ```
  git add src/llm_werewolf/interface/api/models/actions.py src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_control.py && git commit -m "Add GameSessionManager.control() with pause/resume/step/speed

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

### Task 5 — `POST /api/v1/games/{run_id}/control` route

**Files**
- Modify: `src/llm_werewolf/interface/api/routes/actions.py`
- Test: `tests/interface/test_api_control.py` (extend)

Wire the HTTP endpoint to `game_session_manager.control()`, returning 404 when the session is unknown and 400 on validation errors (mirroring `start_game`'s `ValueError → 400`).

- [ ] **Write the failing route test.** Append to `tests/interface/test_api_control.py`:
  ```python
  def test_control_endpoint_unknown_run_404(api_client) -> None:
      resp = api_client.post(
          "/api/v1/games/not-started/control", json={"action": "pause"}
      )
      assert resp.status_code == 404

  def test_control_endpoint_pause(api_client, tmp_path: Path) -> None:
      from llm_werewolf.interface.api.services.game_sessions import (
          game_session_manager,
          GameSessionStatus,
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
  ```

- [ ] **Run ONLY the red pause test, verify it FAILS** (run the already-green 404 test separately in the next step so the red signal is clean — `test_control_endpoint_unknown_run_404` passes for the wrong reason today since *no* route is registered):
  ```
  uv run pytest tests/interface/test_api_control.py::test_control_endpoint_pause -v
  ```
  Expected: `FAILED ... assert 404 == 200` (the POST `/games/ctrl-run/control` path is not registered yet, so FastAPI returns 404 instead of the 200 + paused body the test asserts).

- [ ] **Separately confirm the 404 test currently passes** (it is already-green; isolating it keeps the red phase above unambiguous). It will continue to pass after the route lands because an unknown run still 404s:
  ```
  uv run pytest tests/interface/test_api_control.py::test_control_endpoint_unknown_run_404 -v
  ```
  Expected: `1 passed`.

- [ ] **Add the route.** In `src/llm_werewolf/interface/api/routes/actions.py`, add `ControlGameRequest, ControlGameResponse` to the `from llm_werewolf.interface.api.models.actions import (...)` import block (`:9-21`), then add the route after `cancel_game` (`:169`):
  ```python
  @router.post("/games/{run_id}/control")
  async def control_game(
      run_id: str,
      body: ControlGameRequest,
  ) -> ApiResponse[ControlGameResponse]:
      try:
          data = await game_session_manager.control(
              run_id, action=body.action, value=body.value
          )
      except ValueError as exc:
          raise HTTPException(status_code=400, detail=str(exc)) from exc
      if data is None:
          raise HTTPException(status_code=404, detail=f"Active session not found: {run_id}")
      return ApiResponse(data=data)
  ```

- [ ] **Add the action to `ACTION_SPECS`.** Append a `PageActionSpec` entry inside `ACTION_SPECS` (after the `cancel_game` spec, `:75`):
  ```python
      PageActionSpec(
          page_key="game",
          frontend_route="/game",
          action="control_game",
          method="POST",
          api_path="/api/v1/games/{run_id}/control",
          description="Pause / resume / single-step / set speed for a running game",
          request_model="ControlGameRequest",
          response_model="ControlGameResponse",
      ),
  ```

- [ ] **Run the route tests, verify they PASS.**
  ```
  uv run pytest tests/interface/test_api_control.py::test_control_endpoint_unknown_run_404 tests/interface/test_api_control.py::test_control_endpoint_pause tests/interface/test_api_control.py::test_control_endpoint_rejects_bad_speed -v
  ```
  Expected: all three PASS — unknown run → 404, pause → 200 with `play_state="paused"` / `phase="night"`, speed=3 → 422 from pydantic request validation.

- [ ] **Run the full M2 + adjacent API suite to confirm no regressions.**
  ```
  uv run pytest tests/interface/test_api_control.py tests/interface/test_api_actions.py tests/game_runtime/test_engine_step_equivalence.py tests/game_runtime/test_memory_round_hooks.py -v
  ```
  Expected: all PASS.

- [ ] **Commit.**
  ```
  git add src/llm_werewolf/interface/api/routes/actions.py tests/interface/test_api_control.py && git commit -m "Add POST /games/{run_id}/control route

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

### Task 6 — Wire `play_state`, `speed`, and captured `last_night` into `GET /state`

**Files**
- Modify: `src/llm_werewolf/interface/api/services/state.py` (the M1 live composer)
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py` (the M1 `get_state` picker)
- Test: `tests/interface/test_api_control.py` (extend)

> **DO NOT touch `models/state.py` or `models/actions.py` here.** The `GameStateResponse` model is the single source of truth defined in **M1 Task 2** at `src/llm_werewolf/interface/api/models/state.py`; it ALREADY declares `play_state: PlayState = "playing"`, `speed: int = 1`, and `last_night: LastNight = Field(default_factory=LastNight)` (a typed Pydantic model, not a dict). M2 must NOT re-declare those fields and must NOT add a `last_night: dict[str, Any]` anywhere — that would conflict with the typed `LastNight` model. M2's job is purely to **wire runtime population**: pass the gate-derived `play_state`, the session `speed`, and the captured-before-clear `last_night` snapshot into the existing composer.

`last_night` semantics (spec §5.1 / resolution B): the snapshot captured **before** `next_phase()` clears it (M2 Task 2's `capture_phase_snapshot()` writes `session.last_night`) is the authoritative "last night"; M1's live composition from the current (uncleared) snapshot is the fallback when no capture exists yet. The value is ALWAYS a typed `LastNight`. `build_state_from_snapshot` gains an optional `captured_last_night` argument: when provided it overrides the live `_last_night(snapshot)` composition.

- [ ] **Write the failing `/state` enrichment test.** Append to `tests/interface/test_api_control.py`:
  ```python
  @pytest.mark.asyncio
  async def test_state_reports_play_state_speed_and_last_night(tmp_path: Path) -> None:
      from llm_werewolf.interface.api.services.game_sessions import (
          GameSessionManager,
          GameSessionStatus,
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
  ```

- [ ] **Run it, verify it FAILS.**
  ```
  uv run pytest tests/interface/test_api_control.py::test_state_reports_play_state_speed_and_last_night -v
  ```
  Expected failure: M1's `get_state` ignores the gate/speed/captured snapshot, so `state.play_state == "playing"` and `state.speed == 1` (assertions fail); `status` is still `"running"` not `"paused"`.

- [ ] **Add the `captured_last_night` override to `build_state_from_snapshot`.** In `src/llm_werewolf/interface/api/services/state.py`, change the signature and the `last_night=` line. Replace:
  ```python
  def build_state_from_snapshot(
      snapshot: GameStateSnapshot,
      *,
      status: str,
      error: str | None,
      cursor: int,
      camps: dict[str, str],
  ) -> GameStateResponse:
  ```
  with:
  ```python
  def build_state_from_snapshot(
      snapshot: GameStateSnapshot,
      *,
      status: str,
      error: str | None,
      cursor: int,
      camps: dict[str, str],
      play_state: str = "playing",
      speed: int = 1,
      captured_last_night: LastNight | None = None,
  ) -> GameStateResponse:
  ```
  Then, inside the `return GameStateResponse(...)`, replace `last_night=_last_night(snapshot),` with:
  ```python
          play_state=play_state,
          speed=speed,
          last_night=captured_last_night if captured_last_night is not None else _last_night(snapshot),
  ```

- [ ] **Populate them from the session in `get_state`'s live branch.** In `GameSessionManager.get_state` (M1, `game_sessions.py`), in the `session is not None and session.engine is not None` branch, just before the `return build_state_from_snapshot(...)` call, derive the gate-collapsed status + a typed `LastNight` from the captured dict, then pass them through. Replace the live-branch `return` (M1 Task 5 wrote it at 16-space indent inside `if game_state is not None:`):
  ```python
                return build_state_from_snapshot(
                    snapshot,
                    status=status_map.get(session.status, "running"),
                    error=session.error,
                    cursor=cursor,
                    camps=camps,
                )
  ```
  with:
  ```python
                base_status = status_map.get(session.status, "running")
                play_state = "playing" if session.gate.is_set() else "paused"
                # spec §5.1: a paused RUNNING game collapses status -> "paused"
                status = "paused" if (base_status == "running" and play_state == "paused") else base_status
                captured = _captured_last_night(session.last_night)
                return build_state_from_snapshot(
                    snapshot,
                    status=status,
                    error=session.error,
                    cursor=cursor,
                    camps=camps,
                    play_state=play_state,
                    speed=session.speed,
                    captured_last_night=captured,
                )
  ```
  Add the typed-conversion helper as a module-level function in `game_sessions.py` (near `_seat_of` from Task 2):
  ```python
  def _captured_last_night(captured: dict | None) -> "LastNight | None":
      """Convert a capture_phase_snapshot() dict into the typed LastNight model.

      Returns None when no capture exists yet (live composition is then the fallback).
      """
      from llm_werewolf.interface.api.models.state import LastNight, NightDeath

      if not captured:
          return None
      deaths = [
          NightDeath(seat=d["seat"], cause=d.get("cause"))
          for d in captured.get("deaths", [])
          if isinstance(d, dict) and d.get("seat") is not None
      ]
      return LastNight(
          deaths=deaths,
          saved_seat=captured.get("saved_seat"),
          guarded_seat=captured.get("guarded_seat"),
          poisoned_seat=captured.get("poisoned_seat"),
      )
  ```
  (Add `LastNight` to the `TYPE_CHECKING` import block alongside `GameStateResponse` from M1 Task 5 so the annotation resolves.)

- [ ] **Run the test, verify it PASSES.**
  ```
  uv run pytest tests/interface/test_api_control.py::test_state_reports_play_state_speed_and_last_night -v
  ```
  Expected: PASS — `/state` reports `status="paused"`, `play_state="paused"`, `speed=2`, and `state.last_night.deaths` (attribute access) equals the captured night death.

- [ ] **Run the M1 `/state` tests to confirm backward compatibility.**
  ```
  uv run pytest tests/interface/test_state_service.py tests/interface/test_api_state.py -v
  ```
  Expected: all M1 `/state` tests still PASS (disk fallback keeps the model defaults `play_state="playing"`, `speed=1`, empty `LastNight`).

- [ ] **Commit.**
  ```
  git add src/llm_werewolf/interface/api/services/state.py src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_control.py && git commit -m "Wire play_state, speed, and captured last_night into GET /state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

### Task 7 — Full milestone verification

**Files**
- Test only (no source change)

- [ ] **Run the complete M2 test set plus the engine/integration regression guards.**
  ```
  uv run pytest tests/game_runtime/test_engine_step_equivalence.py tests/game_runtime/test_memory_round_hooks.py tests/interface/test_api_control.py tests/interface/test_api_actions.py tests/integration/test_game_flow.py -v
  ```
  Expected: every test PASSES, with the equivalence test confirming `step()`-pump ≡ `play_game()` (identical final phase/winner/deaths, identical PHASE_CHANGED+GAME_ENDED signature, exactly one GAME_ENDED).

- [ ] **Run the broader engine + interface suites to catch any cross-module regression from the `step()` change.**
  ```
  uv run pytest tests/game_runtime tests/interface -q
  ```
  Expected: all PASS (no `step()` consumer or API test regressed).

- [ ] **Commit any test-only adjustments (if needed).**
  ```
  git add tests && git commit -m "M2 verification: step-pump, control gate, last_night green

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## M3 — Engine signals: missing phase_changed, sub-phase hints, 5 typed skill events, widened role_data

**Coverage:** Covers spec section 6 items 5 (missing phase_changed at sheriff_election / day_voting / ended), 6 (sub_phase signals), 7 (five typed skill events with {actor,target,result}), and the role_data half of item 8 (widen _extract_role_data allowlist for Hunter/Seer). Defines the new EventType enum members and the sub_phase event/value names that the SSE /stream contract in section 5.2 maps to type=phase and type=sub_phase, and that the skill kinds white_wolf_kill / wolf_beauty_charm / nightmare_block / guardian_wolf_guard / raven_mark in section 5.2 are derived from. Keeps events.jsonl / Event.model_dump serialization unchanged (only adds enum members + data fields, no schema change). Does NOT cover EventHub/SSE wiring (M4) or the snapshot-shape additions sub_phase/current_actor_seat/last_night (composed in API layer in M2/M4).

**File structure:**

| File | Action | Responsibility |
|---|---|---|
| `src/llm_werewolf/game_runtime/types/enums.py` | modify | Add new EventType members: SUB_PHASE, WHITE_WOLF_KILLED, WOLF_BEAUTY_CHARMED, NIGHTMARE_BLOCKED, GUARDIAN_WOLF_PROTECTED, RAVEN_MARKED. |
| `src/llm_werewolf/game_runtime/events/event_visibility.py` | modify | Add visibility rules for the new wolf-only/private skill EventTypes so resolve_visible_to keeps the same audience the old MESSAGE rows had (wolf_team or actor-only); keep SUB_PHASE public. |
| `src/llm_werewolf/game_runtime/engine/sheriff_election.py` | modify | Emit PHASE_CHANGED at sheriff_election entry inside execute_sheriff_election. |
| `src/llm_werewolf/game_runtime/engine/voting_phase.py` | modify | Emit PHASE_CHANGED at day_voting entry inside run_voting_phase after set_phase. |
| `src/llm_werewolf/game_runtime/engine/base.py` | modify | Emit PHASE_CHANGED for the ENDED phase inside check_victory (alongside GAME_ENDED, exactly once). |
| `src/llm_werewolf/game_runtime/night_scheduler.py` | modify | Emit lightweight SUB_PHASE events at run_pre_wolf_phase / run_wolf_vote_phase / run_post_wolf_resolution boundaries via a helper. |
| `src/llm_werewolf/game_runtime/engine/night_phase.py` | modify | Emit a SUB_PHASE 'werewolf_chat' event at the start of _run_werewolf_discussion. |
| `src/llm_werewolf/game_runtime/engine/action_processor.py` | modify | Replace the five generic MESSAGE skill logs (white wolf, wolf beauty, nightmare, guardian wolf, raven) with dedicated typed events carrying {actor, target, result}. |
| `src/llm_werewolf/game_runtime/state/serialization.py` | modify | Widen _extract_role_data allowlist so Hunter and Seer serialize skill state (ability_uses, disabled) instead of empty role_data; restore the same fields. |
| `tests/game_runtime/test_enums.py` | create | Assert the new EventType members exist with the expected string values. |
| `tests/game_runtime/test_event_visibility.py` | modify | Assert resolve_visible_to keeps the old audience for the new skill EventTypes and that SUB_PHASE is public. |
| `tests/game_runtime/test_action_processor.py` | modify | Assert each of the five formerly-untyped skills now logs its dedicated EventType with actor_id/target_id/result data. |
| `tests/game_runtime/test_night_sub_phase_signals.py` | create | Assert NightSkillScheduler and _run_werewolf_discussion emit SUB_PHASE events with the expected name values. |
| `tests/game_runtime/test_phase_changed_signals.py` | create | Assert PHASE_CHANGED is emitted at sheriff_election, day_voting, and ended entry. |
| `tests/game_runtime/test_role_data_widening.py` | create | Assert serialize_player produces non-empty role_data for Hunter and Seer and round-trips. |
| `tests/game_runtime/test_serialize_parity.py` | create | Spec §9: assert the live build_state_from_snapshot /state equals the disk build_state_from_view /state mid-game (phase/round/alive/dead/sheriff/winner/votes + widened Hunter/Seer role_data). |

> Conventions for every task below:
> - Backend tests: `uv run pytest <path> -v` (run from the worktree root `D:/AI_werewolf/Frontend_6_3/MultiAgent-Werewolf/.claude/worktrees/engine-driven-api`).
> - Commit after each green test.
> - All `_log_event` calls go through `GameEngineBase._log_event` (or the scheduler's injected `log_event` callable), which assigns `phase`/`round_number` and resolves `visible_to` via `resolve_visible_to`. Disk serialization is `Event.model_dump(mode="json")` and is unchanged by adding enum members + data fields.

---

### Task 1 — Add the new EventType enum members

**Files**
- Modify: `src/llm_werewolf/game_runtime/types/enums.py`
- Create (test): `tests/game_runtime/test_enums.py`

- [ ] Write the failing test `tests/game_runtime/test_enums.py`:
```python
"""game_runtime/types/enums.py 的事件类型测试。"""

from llm_werewolf.game_runtime.types import EventType


def test_sub_phase_event_type_exists() -> None:
    assert EventType.SUB_PHASE.value == "sub_phase"


def test_typed_skill_event_types_exist() -> None:
    assert EventType.WHITE_WOLF_KILLED.value == "white_wolf_killed"
    assert EventType.WOLF_BEAUTY_CHARMED.value == "wolf_beauty_charmed"
    assert EventType.NIGHTMARE_BLOCKED.value == "nightmare_blocked"
    assert EventType.GUARDIAN_WOLF_PROTECTED.value == "guardian_wolf_protected"
    assert EventType.RAVEN_MARKED.value == "raven_marked"
```

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_enums.py -v
```
Expected: `AttributeError: SUB_PHASE` (the enum members do not exist yet).

- [ ] Add the members to `EventType` in `src/llm_werewolf/game_runtime/types/enums.py`. Insert `SUB_PHASE` right after `PHASE_CHANGED`, and add the five typed skill members after `GRAVEYARD_KEEPER_CHECK`:
```python
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    PHASE_CHANGED = "phase_changed"
    SUB_PHASE = "sub_phase"
    ROUND_STARTED = "round_started"
```
```python
    WEREWOLF_KILLED = "werewolf_killed"
    WITCH_SAVED = "witch_saved"
    WITCH_POISONED = "witch_poisoned"
    SEER_CHECKED = "seer_checked"
    GUARD_PROTECTED = "guard_protected"
    GRAVEYARD_KEEPER_CHECK = "graveyard_keeper_check"
    WHITE_WOLF_KILLED = "white_wolf_killed"
    WOLF_BEAUTY_CHARMED = "wolf_beauty_charmed"
    NIGHTMARE_BLOCKED = "nightmare_blocked"
    GUARDIAN_WOLF_PROTECTED = "guardian_wolf_protected"
    RAVEN_MARKED = "raven_marked"
```

- [ ] Run the test, verify it PASSES:
```
uv run pytest tests/game_runtime/test_enums.py -v
```
Expected: `2 passed`.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/types/enums.py tests/game_runtime/test_enums.py && git commit -m "Add SUB_PHASE and five typed skill EventType members

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2 — Default visibility for the new skill EventTypes (preserve old audiences)

The old generic `MESSAGE` rows for these skills resolved visibility as: White Wolf kill and Guardian Wolf protect were `wolf_team` (had `data["visibility"] == "wolf_team"`); Wolf Beauty charm, Nightmare block, and Raven mark had `data["player_id"]` (so `resolve_visible_to` returned `[actor_id]`). We must keep the same audiences now that they carry dedicated EventTypes.

**Files**
- Modify: `src/llm_werewolf/game_runtime/events/event_visibility.py`
- Modify (test): `tests/game_runtime/test_event_visibility.py`

- [ ] Add the failing tests to `tests/game_runtime/test_event_visibility.py` (append at end of file):
```python
def test_white_wolf_and_guardian_wolf_visible_to_wolf_team() -> None:
    wolves = ["w1", "w2"]
    assert resolve_visible_to(
        EventType.WHITE_WOLF_KILLED, {"target_id": "v1"}, wolf_player_ids=wolves
    ) == ["w1", "w2"]
    assert resolve_visible_to(
        EventType.GUARDIAN_WOLF_PROTECTED, {"actor_id": "w2", "target_id": "w1"},
        wolf_player_ids=wolves,
    ) == ["w1", "w2"]


def test_wolf_beauty_nightmare_raven_visible_to_actor_only() -> None:
    for event_type in (
        EventType.WOLF_BEAUTY_CHARMED,
        EventType.NIGHTMARE_BLOCKED,
        EventType.RAVEN_MARKED,
    ):
        assert resolve_visible_to(
            event_type, {"actor_id": "a1", "target_id": "t1"}, wolf_player_ids=["a1"]
        ) == ["a1"]


def test_sub_phase_is_public() -> None:
    assert resolve_visible_to(EventType.SUB_PHASE, {"name": "werewolf_chat"}) is None
```
Confirm the import line at the top of the test file already reads `from llm_werewolf.game_runtime.events.event_visibility import resolve_visible_to` and imports `EventType`; if not, add them.

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_event_visibility.py::test_white_wolf_and_guardian_wolf_visible_to_wolf_team tests/game_runtime/test_event_visibility.py::test_wolf_beauty_nightmare_raven_visible_to_actor_only tests/game_runtime/test_event_visibility.py::test_sub_phase_is_public -v
```
Expected: the wolf-team and actor-only tests FAIL (returning `None` because these types fall through to the default `return None`); `test_sub_phase_is_public` already PASSES.

- [ ] Add the new rules to `resolve_visible_to` in `src/llm_werewolf/game_runtime/events/event_visibility.py`. First add the new module-level sets after `WITCH_ONLY_TYPES`:
```python
# 仅狼队 observation 可见的定向技能事件。
WOLF_TEAM_SKILL_TYPES: frozenset[EventType] = frozenset({
    EventType.WHITE_WOLF_KILLED,
    EventType.GUARDIAN_WOLF_PROTECTED,
})

# 仅行动者本人 observation 可见的定向技能事件。
ACTOR_ONLY_SKILL_TYPES: frozenset[EventType] = frozenset({
    EventType.WOLF_BEAUTY_CHARMED,
    EventType.NIGHTMARE_BLOCKED,
    EventType.RAVEN_MARKED,
})
```
Then add the branches at the top of `resolve_visible_to`, immediately after the `WITCH_ONLY_TYPES` check:
```python
    if event_type in WOLF_TEAM_SKILL_TYPES:
        return list(wolf_player_ids) if wolf_player_ids else []

    if event_type in ACTOR_ONLY_SKILL_TYPES:
        actor_id = (data or {}).get("actor_id")
        return [actor_id] if actor_id else None
```
(`SUB_PHASE` needs no branch; it falls through to `return None` = public, which the test already expects.)

- [ ] Run the tests, verify they PASS:
```
uv run pytest tests/game_runtime/test_event_visibility.py -v
```
Expected: all tests in the file pass (existing + 3 new).

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/events/event_visibility.py tests/game_runtime/test_event_visibility.py && git commit -m "Resolve visibility for typed skill events to preserve old audiences

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3 — Five typed skill events with {actor, target, result}

Replace the five `EventType.MESSAGE` logs in `action_processor.py` with dedicated typed events. The data shape standardizes on `actor_id`, `target_id`, and `result` (so the SSE `skill` payload in §5.2 maps `actor {seat}`, `target {seat}`, `result` directly). `result` is the action's executed outcome string already returned by `action.execute()` — but `_log_action_event` does not receive it, so we derive a stable result token per skill from game state instead.

**Files**
- Modify: `src/llm_werewolf/game_runtime/engine/action_processor.py`
- Modify (test): `tests/game_runtime/test_action_processor.py`

- [ ] Add the failing tests to `tests/game_runtime/test_action_processor.py`. First extend the existing imports at the top of the file:
```python
from llm_werewolf.game_runtime.roles import (
    Seer,
    Guard,
    Witch,
    Raven,
    Villager,
    Werewolf,
    WolfBeauty,
    WhiteWolf,
    NightmareWolf,
    GuardianWolf,
)
from llm_werewolf.game_runtime.types import EventType, ActionPriority
from llm_werewolf.game_runtime.actions.werewolf import (
    WerewolfVoteAction,
    WhiteWolfKillAction,
    WolfBeautyCharmAction,
    NightmareWolfBlockAction,
    GuardianWolfProtectAction,
)
from llm_werewolf.game_runtime.actions.villager import (
    SeerCheckAction,
    WitchSaveAction,
    WitchPoisonAction,
    GuardProtectAction,
    RavenMarkAction,
)
```
Then append the new tests:
```python
def test_log_white_wolf_action_emits_typed_event() -> None:
    white = Player("w1", "White", WhiteWolf)
    target = Player("w2", "Wolf", Werewolf)
    state = GameState([white, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_white_wolf_action(WhiteWolfKillAction(white, target, state))

    event_type, _message = processor._log_event.call_args.args[:2]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.WHITE_WOLF_KILLED
    assert data["actor_id"] == "w1"
    assert data["target_id"] == "w2"
    assert data["result"] == "killed"


def test_log_wolf_beauty_action_emits_typed_event() -> None:
    beauty = Player("b1", "Beauty", WolfBeauty)
    target = Player("v1", "Villager", Villager)
    state = GameState([beauty, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_wolf_beauty_action(WolfBeautyCharmAction(beauty, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.WOLF_BEAUTY_CHARMED
    assert data["actor_id"] == "b1"
    assert data["target_id"] == "v1"
    assert data["result"] == "charmed"


def test_log_nightmare_block_action_emits_typed_event() -> None:
    nightmare = Player("n1", "Nightmare", NightmareWolf)
    target = Player("s1", "Seer", Seer)
    state = GameState([nightmare, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_nightmare_block_action(NightmareWolfBlockAction(nightmare, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.NIGHTMARE_BLOCKED
    assert data["actor_id"] == "n1"
    assert data["target_id"] == "s1"
    assert data["result"] == "blocked"


def test_log_guardian_wolf_action_emits_typed_event() -> None:
    guardian = Player("g1", "Guardian", GuardianWolf)
    target = Player("w2", "Wolf", Werewolf)
    state = GameState([guardian, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_guardian_wolf_action(GuardianWolfProtectAction(guardian, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.GUARDIAN_WOLF_PROTECTED
    assert data["actor_id"] == "g1"
    assert data["target_id"] == "w2"
    assert data["result"] == "protected"


def test_log_raven_action_emits_typed_event() -> None:
    raven = Player("r1", "Raven", Raven)
    target = Player("v1", "Villager", Villager)
    state = GameState([raven, target])
    state.round_number = 1
    processor = _Processor(state)

    processor._log_raven_action(RavenMarkAction(raven, target, state))

    event_type = processor._log_event.call_args.args[0]
    data = processor._log_event.call_args.kwargs["data"]
    assert event_type == EventType.RAVEN_MARKED
    assert data["actor_id"] == "r1"
    assert data["target_id"] == "v1"
    assert data["result"] == "marked"
```

- [ ] Run them, verify they FAIL:
```
uv run pytest tests/game_runtime/test_action_processor.py -k "emits_typed_event" -v
```
Expected: 5 failures. The asserts on `event_type == EventType.WHITE_WOLF_KILLED` fail because the methods still log `EventType.MESSAGE`, and `data["actor_id"]` raises `KeyError` (current code uses `player_id` / `target_id` only). (If `WhiteWolf`/`GuardianWolf` are not exported by `roles/__init__.py`, the import fails first — in that case fix the import to `from llm_werewolf.game_runtime.roles.werewolf import WhiteWolf, GuardianWolf` and re-run.)

- [ ] Rewrite the five `_log_*` methods in `src/llm_werewolf/game_runtime/engine/action_processor.py`. Replace `_log_white_wolf_action` through `_log_raven_action` (lines 177-236) with:
```python
    def _log_white_wolf_action(self, action: WhiteWolfKillAction) -> None:
        """记录白狼王击杀行动（定向技能事件，仅狼队可见）。"""
        self._log_event(
            EventType.WHITE_WOLF_KILLED,
            self.locale.get("white_wolf_kills", target=action.target.name),
            data={
                "actor_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "result": "killed",
                "visibility": "wolf_team",
                **self._decision_data(action),
            },
        )

    def _log_wolf_beauty_action(self, action: WolfBeautyCharmAction) -> None:
        """记录狼美人魅惑行动（定向技能事件，仅行动者可见）。"""
        self._log_event(
            EventType.WOLF_BEAUTY_CHARMED,
            self.locale.get("wolf_beauty_charms", target=action.target.name),
            data={
                "actor_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "result": "charmed",
                **self._decision_data(action),
            },
        )

    def _log_nightmare_block_action(self, action: NightmareWolfBlockAction) -> None:
        """记录梦魇狼封锁行动（定向技能事件，仅行动者可见）。"""
        self._log_event(
            EventType.NIGHTMARE_BLOCKED,
            self.locale.get("nightmare_blocks", target=action.target.name),
            data={
                "actor_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "result": "blocked",
                **self._decision_data(action),
            },
        )

    def _log_guardian_wolf_action(self, action: GuardianWolfProtectAction) -> None:
        """记录守墓狼保护行动（定向技能事件，仅狼队可见）。"""
        self._log_event(
            EventType.GUARDIAN_WOLF_PROTECTED,
            self.locale.get("guardian_wolf_protected", target=action.target.name),
            data={
                "actor_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "result": "protected",
                "visibility": "wolf_team",
                **self._decision_data(action),
            },
        )

    def _log_raven_action(self, action: RavenMarkAction) -> None:
        """记录乌鸦标记行动（定向技能事件，仅行动者可见）。"""
        self._log_event(
            EventType.RAVEN_MARKED,
            self.locale.get("raven_marks", target=action.target.name),
            data={
                "actor_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "result": "marked",
                **self._decision_data(action),
            },
        )
```
(Note: `visibility: "wolf_team"` in data is harmless and kept for parity with the prior rows; the dedicated EventType branches added in Task 2 already resolve the audience. The `actor_id`/`target_id` keys are what Task 2's `ACTOR_ONLY_SKILL_TYPES` branch reads.)

- [ ] Run the new tests, verify they PASS:
```
uv run pytest tests/game_runtime/test_action_processor.py -k "emits_typed_event" -v
```
Expected: `5 passed`.

- [ ] Run the full action_processor test file to confirm no regression:
```
uv run pytest tests/game_runtime/test_action_processor.py -v
```
Expected: all pass.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/engine/action_processor.py tests/game_runtime/test_action_processor.py && git commit -m "Emit typed skill events for white wolf/wolf beauty/nightmare/guardian wolf/raven

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4 — SUB_PHASE signals from NightSkillScheduler boundaries

Emit a lightweight `SUB_PHASE` event at each scheduler boundary so the frontend can highlight night sub-steps. The scheduler already holds `self._log_event` (injected from `run_night_phase`). Each event's `data["name"]` is the display hint.

**Files**
- Modify: `src/llm_werewolf/game_runtime/night_scheduler.py`
- Create (test): `tests/game_runtime/test_night_sub_phase_signals.py`

- [ ] Write the failing test `tests/game_runtime/test_night_sub_phase_signals.py`:
```python
"""NightSkillScheduler 与狼队夜聊的 SUB_PHASE 信号测试。"""

import asyncio
from unittest.mock import MagicMock

from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.night_scheduler import NightSkillScheduler


def _sub_phase_names(log_event: MagicMock) -> list[str]:
    names = []
    for call in log_event.call_args_list:
        if call.args and call.args[0] == EventType.SUB_PHASE:
            names.append(call.kwargs["data"]["name"])
    return names


def _scheduler(log_event: MagicMock) -> NightSkillScheduler:
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    state = GameState([wolf, villager])
    state.round_number = 1
    return NightSkillScheduler(
        state,
        log_event=log_event,
        locale=MagicMock(),
        resolve_werewolf_votes=lambda: [],
    )


def test_run_pre_wolf_phase_emits_pre_wolf_sub_phase() -> None:
    log_event = MagicMock()
    scheduler = _scheduler(log_event)
    asyncio.run(scheduler.run_pre_wolf_phase())
    assert "pre_wolf" in _sub_phase_names(log_event)


def test_run_wolf_vote_phase_emits_werewolf_kill_sub_phase() -> None:
    log_event = MagicMock()
    scheduler = _scheduler(log_event)
    asyncio.run(scheduler.run_wolf_vote_phase())
    assert "werewolf_kill" in _sub_phase_names(log_event)


def test_run_post_wolf_resolution_emits_witch_then_seer_sub_phases() -> None:
    log_event = MagicMock()
    scheduler = _scheduler(log_event)
    asyncio.run(scheduler.run_post_wolf_resolution())
    names = _sub_phase_names(log_event)
    assert "witch_decide" in names
    assert "seer_check" in names
```

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_night_sub_phase_signals.py -v
```
Expected: 3 failures — no `SUB_PHASE` events are emitted yet (`_sub_phase_names` returns `[]`).

- [ ] Add a `_emit_sub_phase` helper and call it at each boundary in `src/llm_werewolf/game_runtime/night_scheduler.py`. Add the helper inside `NightSkillScheduler` (after `__init__`):
```python
    def _emit_sub_phase(self, name: str) -> None:
        """发出轻量级 SUB_PHASE 显示提示（非 GamePhase，非暂停点）。"""
        self._log_event(
            EventType.SUB_PHASE,
            "",
            data={"name": name},
        )
```
Then emit at the three boundaries:
```python
    async def run_pre_wolf_phase(self) -> list[Action]:
        """丘比特、梦魇狼、守卫等——在狼票之前。"""
        self._emit_sub_phase("pre_wolf")
        return await self._collect_for_players(self._players_pre_wolf())

    async def run_wolf_vote_phase(self) -> list[Action]:
        """仅收集狼队击杀投票。"""
        self._emit_sub_phase("werewolf_kill")
        return await self._collect_for_players(self._players_werewolf_voters())

    async def run_post_wolf_resolution(self) -> list[Action]:
        """女巫（在 ``werewolf_target`` 确定后），随后预言家 / 守墓人 / 乌鸦。"""
        actions: list[Action] = []
        self._emit_sub_phase("witch_decide")
        actions.extend(await self._collect_for_players(self._players_witch()))
        self._emit_sub_phase("seer_check")
        actions.extend(await self._collect_for_players(self._players_post_witch_ordered()))
        return actions
```

- [ ] Run the test, verify it PASSES:
```
uv run pytest tests/game_runtime/test_night_sub_phase_signals.py -v
```
Expected: `3 passed`.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/night_scheduler.py tests/game_runtime/test_night_sub_phase_signals.py && git commit -m "Emit SUB_PHASE signals at night scheduler boundaries

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5 — SUB_PHASE 'werewolf_chat' at werewolf discussion start

**Files**
- Modify: `src/llm_werewolf/game_runtime/engine/night_phase.py`
- Modify (test): `tests/game_runtime/test_night_sub_phase_signals.py`

- [ ] Add the failing test to `tests/game_runtime/test_night_sub_phase_signals.py` (append). It drives `_run_werewolf_discussion` through a minimal subclass that stubs the discussion plumbing:
```python
from llm_werewolf.game_runtime.engine.night_phase import NightPhaseMixin
from llm_werewolf.game_runtime.locale import Locale


class _NightHarness(NightPhaseMixin):
    def __init__(self, game_state: GameState, log_event: MagicMock) -> None:
        self.game_state = game_state
        self.locale = Locale("en-US")
        self._log_event = log_event

    def build_shared_observation(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return ""


def test_run_werewolf_discussion_emits_werewolf_chat_sub_phase() -> None:
    log_event = MagicMock()
    wolf_a = Player("w1", "WolfA", Werewolf)
    wolf_b = Player("w2", "WolfB", Werewolf)
    villager = Player("v1", "Villager", Villager)
    state = GameState([wolf_a, wolf_b, villager])
    state.round_number = 1

    class _Interaction:
        async def run_roundtable(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

    state.phase_interaction = _Interaction()
    harness = _NightHarness(state, log_event)

    asyncio.run(harness._run_werewolf_discussion())

    names = _sub_phase_names(log_event)
    assert "werewolf_chat" in names
```
(`require_phase_interaction()` returns `self.phase_interaction`; the stub's `run_roundtable` is awaited and returns immediately. Two alive wolves are required so the early `len(werewolves) <= 1` return is not taken.)

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_night_sub_phase_signals.py::test_run_werewolf_discussion_emits_werewolf_chat_sub_phase -v
```
Expected: failure — `"werewolf_chat"` not in emitted SUB_PHASE names.

- [ ] In `src/llm_werewolf/game_runtime/engine/night_phase.py`, inside `_run_werewolf_discussion`, emit the sub-phase right after the early `len(werewolves) <= 1` guard and before the `narrator_werewolves_wake` MESSAGE. Change:
```python
        if len(werewolves) <= 1:
            return messages

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_wake"),
            data={"action": "werewolves_wake"},
        )
```
to:
```python
        if len(werewolves) <= 1:
            return messages

        self._log_event(
            EventType.SUB_PHASE,
            "",
            data={"name": "werewolf_chat"},
        )

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_wake"),
            data={"action": "werewolves_wake"},
        )
```

- [ ] Run the test, verify it PASSES:
```
uv run pytest tests/game_runtime/test_night_sub_phase_signals.py -v
```
Expected: all tests in the file pass.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/engine/night_phase.py tests/game_runtime/test_night_sub_phase_signals.py && git commit -m "Emit werewolf_chat SUB_PHASE at werewolf discussion start

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6 — PHASE_CHANGED at sheriff_election entry

**Files**
- Modify: `src/llm_werewolf/game_runtime/engine/sheriff_election.py`
- Create (test): `tests/game_runtime/test_phase_changed_signals.py`

- [ ] Write the failing test `tests/game_runtime/test_phase_changed_signals.py`:
```python
"""引擎缺失的 PHASE_CHANGED 信号测试（警长选举 / 投票 / 结束）。"""

import asyncio
from unittest.mock import MagicMock

from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.types import EventType, GamePhase
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.engine.sheriff_election import SheriffElectionMixin


def _phase_changed_phases(log_event: MagicMock) -> list[str]:
    phases = []
    for call in log_event.call_args_list:
        if call.args and call.args[0] == EventType.PHASE_CHANGED:
            data = call.kwargs.get("data") or {}
            phases.append(data.get("phase"))
    return phases


class _SheriffHarness(SheriffElectionMixin):
    def __init__(self, game_state: GameState, log_event: MagicMock) -> None:
        self.game_state = game_state
        self.locale = Locale("en-US")
        self._log_event = log_event


def test_sheriff_election_emits_phase_changed() -> None:
    log_event = MagicMock()
    state = GameState([Player("v1", "V1", Villager)])
    state.set_phase(GamePhase.SHERIFF_ELECTION)
    state.round_number = 1
    harness = _SheriffHarness(state, log_event)

    asyncio.run(harness.execute_sheriff_election())

    assert GamePhase.SHERIFF_ELECTION.value in _phase_changed_phases(log_event)
```
(With a single non-agent player, `_collect_sheriff_candidates` returns `[]`, so `execute_sheriff_election` returns early after the campaign-started log — the PHASE_CHANGED must be emitted before that early return.)

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_phase_changed_signals.py::test_sheriff_election_emits_phase_changed -v
```
Expected: failure — `"sheriff_election"` not in `_phase_changed_phases` (no PHASE_CHANGED currently emitted in this phase).

- [ ] In `src/llm_werewolf/game_runtime/engine/sheriff_election.py`, emit PHASE_CHANGED at the very start of `execute_sheriff_election`, before the `SHERIFF_CAMPAIGN_STARTED` log:
```python
    async def execute_sheriff_election(self) -> None:
        """执行警长选举阶段。"""
        if not self.game_state:
            return

        self._log_event(
            EventType.PHASE_CHANGED,
            self.locale.get("sheriff_campaign_started"),
            data={
                "phase": GamePhase.SHERIFF_ELECTION.value,
                "round": self.game_state.round_number,
            },
        )

        self._log_event(
            EventType.SHERIFF_CAMPAIGN_STARTED, self.locale.get("sheriff_campaign_started")
        )
```

- [ ] Run the test, verify it PASSES:
```
uv run pytest tests/game_runtime/test_phase_changed_signals.py::test_sheriff_election_emits_phase_changed -v
```
Expected: `1 passed`.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/engine/sheriff_election.py tests/game_runtime/test_phase_changed_signals.py && git commit -m "Emit PHASE_CHANGED at sheriff_election entry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7 — PHASE_CHANGED at day_voting entry

**Files**
- Modify: `src/llm_werewolf/game_runtime/engine/voting_phase.py`
- Modify (test): `tests/game_runtime/test_phase_changed_signals.py`

- [ ] Add the failing test to `tests/game_runtime/test_phase_changed_signals.py` (append). It drives `run_voting_phase` via a harness whose collaborators are no-ops, so only the phase-entry log matters:
```python
from llm_werewolf.game_runtime.engine.voting_phase import VotingPhaseMixin


class _VotingHarness(VotingPhaseMixin):
    def __init__(self, game_state: GameState, log_event: MagicMock) -> None:
        self.game_state = game_state
        self.locale = Locale("en-US")
        self._log_event = log_event

    async def _handle_knight_duel(self):  # noqa: ANN202
        return []

    async def _handle_death_abilities(self):  # noqa: ANN202
        return []


def test_voting_phase_emits_phase_changed() -> None:
    log_event = MagicMock()
    state = GameState([Player("v1", "V1", Villager), Player("w1", "W1", Werewolf)])
    state.set_phase(GamePhase.DAY_DISCUSSION)
    state.round_number = 1
    harness = _VotingHarness(state, log_event)

    asyncio.run(harness.run_voting_phase())

    assert GamePhase.DAY_VOTING.value in _phase_changed_phases(log_event)
```
(Players have no `agent`, so `_collect_votes` returns `[]` and the `if vote_counts:` branch is skipped; the phase-entry PHASE_CHANGED is the assertion.)

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_phase_changed_signals.py::test_voting_phase_emits_phase_changed -v
```
Expected: failure — `"day_voting"` not in `_phase_changed_phases`.

- [ ] In `src/llm_werewolf/game_runtime/engine/voting_phase.py`, emit PHASE_CHANGED at the top of `run_voting_phase` right after `set_phase(GamePhase.DAY_VOTING)`:
```python
        messages = []
        self.game_state.set_phase(GamePhase.DAY_VOTING)
        self.game_state.vote_tie_count = 0

        self._log_event(
            EventType.PHASE_CHANGED,
            self.locale.get("voting_phase_separator"),
            data={
                "phase": GamePhase.DAY_VOTING.value,
                "round": self.game_state.round_number,
            },
        )

        messages.append(self.locale.get("voting_phase_separator"))
```

- [ ] Run the test, verify it PASSES:
```
uv run pytest tests/game_runtime/test_phase_changed_signals.py::test_voting_phase_emits_phase_changed -v
```
Expected: `1 passed`.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/engine/voting_phase.py tests/game_runtime/test_phase_changed_signals.py && git commit -m "Emit PHASE_CHANGED at day_voting entry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8 — PHASE_CHANGED at ended entry (alongside GAME_ENDED, exactly once)

`check_victory` already sets `phase = ENDED` and emits `GAME_ENDED`. Add a single PHASE_CHANGED for the ended phase next to it, inside the same `if result.has_winner:` block so it fires exactly once.

**Files**
- Modify: `src/llm_werewolf/game_runtime/engine/base.py`
- Modify (test): `tests/game_runtime/test_phase_changed_signals.py`

- [ ] Add the failing test to `tests/game_runtime/test_phase_changed_signals.py` (append). It builds a real `GameEngineBase`, forces a victory, captures events, and asserts exactly one PHASE_CHANGED with phase `ended` and exactly one GAME_ENDED:
```python
from llm_werewolf.game_runtime.engine.base import GameEngineBase
from llm_werewolf.game_runtime.types import VictoryResult


def test_check_victory_emits_single_ended_phase_changed() -> None:
    captured = []
    engine = GameEngineBase()
    engine.game_state = GameState([Player("v1", "V1", Villager), Player("w1", "W1", Werewolf)])
    engine.game_state.round_number = 1
    engine.on_event = captured.append

    engine.victory_checker = MagicMock()
    engine.victory_checker.check_victory.return_value = VictoryResult(
        has_winner=True, winner_camp="villager", winner_ids=["v1"], reason="all wolves dead"
    )

    assert engine.check_victory() is True

    ended_phase_changes = [
        e
        for e in captured
        if e.event_type == EventType.PHASE_CHANGED
        and (e.data or {}).get("phase") == GamePhase.ENDED.value
    ]
    game_ended = [e for e in captured if e.event_type == EventType.GAME_ENDED]
    assert len(ended_phase_changes) == 1
    assert len(game_ended) == 1
```

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_phase_changed_signals.py::test_check_victory_emits_single_ended_phase_changed -v
```
Expected: failure — `len(ended_phase_changes) == 0` (no PHASE_CHANGED for ENDED today).

- [ ] In `src/llm_werewolf/game_runtime/engine/base.py`, inside `check_victory`, add the PHASE_CHANGED emit right before the existing `GAME_ENDED` log. Change:
```python
            self._log_event(
                EventType.GAME_ENDED,
                self.locale.get("game_ended", winner=result.winner_camp, reason=result.reason),
                data={
                    "winner_camp": result.winner_camp,
                    "winner_ids": result.winner_ids,
                    "reason": result.reason,
                },
            )

            return True
```
to:
```python
            self._log_event(
                EventType.PHASE_CHANGED,
                self.locale.get("game_ended", winner=result.winner_camp, reason=result.reason),
                data={
                    "phase": GamePhase.ENDED.value,
                    "round": self.game_state.round_number if self.game_state else 0,
                },
            )

            self._log_event(
                EventType.GAME_ENDED,
                self.locale.get("game_ended", winner=result.winner_camp, reason=result.reason),
                data={
                    "winner_camp": result.winner_camp,
                    "winner_ids": result.winner_ids,
                    "reason": result.reason,
                },
            )

            return True
```

- [ ] Run the test, verify it PASSES:
```
uv run pytest tests/game_runtime/test_phase_changed_signals.py::test_check_victory_emits_single_ended_phase_changed -v
```
Expected: `1 passed`.

- [ ] Run the whole phase-changed file to confirm no regression:
```
uv run pytest tests/game_runtime/test_phase_changed_signals.py -v
```
Expected: all pass.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/engine/base.py tests/game_runtime/test_phase_changed_signals.py && git commit -m "Emit single PHASE_CHANGED for ended phase in check_victory

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9 — Widen _extract_role_data for Hunter and Seer

Hunter and Seer carry no role-specific stored fields beyond the base `Role` attributes `ability_uses` (int) and `disabled` (bool). Widen the allowlist so they serialize `{"ability_uses": ..., "disabled": ...}` instead of empty `role_data`, and restore those fields on load. This keeps the snapshot complete for the spectator `/state` per spec §6.8.

**Files**
- Modify: `src/llm_werewolf/game_runtime/state/serialization.py`
- Create (test): `tests/game_runtime/test_role_data_widening.py`

- [ ] Write the failing test `tests/game_runtime/test_role_data_widening.py`:
```python
"""Hunter / Seer 的 role_data 序列化加宽测试。"""

from llm_werewolf.game_runtime.roles import Seer, Hunter, Villager
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.state.serialization import (
    serialize_player,
    restore_game_state,
    serialize_game_state,
)


def test_hunter_role_data_serialized() -> None:
    hunter = Player("h1", "Hunter", Hunter)
    hunter.role.ability_uses = 1
    hunter.role.disabled = True

    snap = serialize_player(hunter)

    assert snap.role_data == {"ability_uses": 1, "disabled": True}


def test_seer_role_data_serialized() -> None:
    seer = Player("s1", "Seer", Seer)

    snap = serialize_player(seer)

    assert snap.role_data == {"ability_uses": 0, "disabled": False}


def test_hunter_role_data_roundtrip() -> None:
    hunter = Player("h1", "Hunter", Hunter)
    hunter.role.ability_uses = 1
    state = GameState([hunter, Player("v1", "V1", Villager)])

    snap = serialize_game_state(state)
    restored = restore_game_state(snap)

    restored_hunter = restored.get_player("h1")
    assert restored_hunter.role.ability_uses == 1
```

- [ ] Run it, verify it FAILS:
```
uv run pytest tests/game_runtime/test_role_data_widening.py -v
```
Expected: `test_hunter_role_data_serialized` and `test_seer_role_data_serialized` fail (`role_data == {}` today); `test_hunter_role_data_roundtrip` fails (`ability_uses` resets to 0 because nothing restores it).

- [ ] In `src/llm_werewolf/game_runtime/state/serialization.py`, add `Seer`/`Hunter` to the imports from `roles.villager`:
```python
from llm_werewolf.game_runtime.roles.villager import (
    Cupid,
    Elder,
    Seer,
    Guard,
    Idiot,
    Witch,
    Hunter,
    Knight,
    Magician,
)
```
Add them to the `simple_extractors` map in `_extract_role_data`:
```python
    simple_extractors = {
        Guard: lambda r: {"last_protected": r.last_protected},
        Elder: lambda r: {"lives": r.lives},
        Idiot: lambda r: {"revealed": r.revealed},
        WolfBeauty: lambda r: {"charmed_player": r.charmed_player},
        Knight: lambda r: {"has_dueled": r.has_dueled},
        Cupid: lambda r: {"has_linked": r.has_linked},
        BloodMoonApostle: lambda r: {"transformed": r.transformed},
        Magician: lambda r: {"has_swapped": r.has_swapped},
        Thief: lambda r: {"has_chosen": r.has_chosen},
        Seer: lambda r: {"ability_uses": r.ability_uses, "disabled": r.disabled},
        Hunter: lambda r: {"ability_uses": r.ability_uses, "disabled": r.disabled},
    }
```
And to the `simple_restorers` map in `_restore_role_data`:
```python
    simple_restorers = {
        Guard: lambda r, d: setattr(r, "last_protected", d.get("last_protected")),
        Elder: lambda r, d: setattr(r, "lives", d.get("lives", 2)),
        Idiot: lambda r, d: setattr(r, "revealed", d.get("revealed", False)),
        WolfBeauty: lambda r, d: setattr(r, "charmed_player", d.get("charmed_player")),
        Knight: lambda r, d: setattr(r, "has_dueled", d.get("has_dueled", False)),
        Cupid: lambda r, d: setattr(r, "has_linked", d.get("has_linked", False)),
        BloodMoonApostle: lambda r, d: setattr(r, "transformed", d.get("transformed", False)),
        Magician: lambda r, d: setattr(r, "has_swapped", d.get("has_swapped", False)),
        Thief: lambda r, d: setattr(r, "has_chosen", d.get("has_chosen", False)),
        Seer: lambda r, d: _restore_base_skill_state(r, d),
        Hunter: lambda r, d: _restore_base_skill_state(r, d),
    }
```
Add the helper `_restore_base_skill_state` just above `_restore_role_data`:
```python
def _restore_base_skill_state(role: object, role_data: dict[str, Any]) -> None:
    """恢复基础角色技能状态（ability_uses / disabled）。"""
    role.ability_uses = role_data.get("ability_uses", 0)
    role.disabled = role_data.get("disabled", False)
```

- [ ] Run the test, verify it PASSES:
```
uv run pytest tests/game_runtime/test_role_data_widening.py -v
```
Expected: `3 passed`.

- [ ] Commit:
```
git add src/llm_werewolf/game_runtime/state/serialization.py tests/game_runtime/test_role_data_widening.py && git commit -m "Serialize Hunter/Seer skill state in role_data

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9x — `serialize_game_state` round-trip parity with `build_view` (spec §9)

Spec §9 (first bullet) requires: *every field `build_view` reconstructed is present and correct mid-game* in the live `/state`, including the widened `role_data` for Hunter/Seer. M3 Task 9 only covered `role_data` shape in isolation; this task asserts the **whole** `/state` snapshot (the live `build_state_from_snapshot` path) equals the disk-reconstructed `/state` (the `build_state_from_view` path) for the same mid-game position. This guards the engine-vs-log contract at the field level: phase, round, alive/dead seats, sheriff, winner, votes, and player role_data must agree.

**Files**
- Create (test): `tests/game_runtime/test_serialize_parity.py`

This is a parity assertion over already-implemented code (M1's two composers + M3's widening), so there is no new production code — but the test is genuinely red until M3's role_data widening (Task 9) and M1's composers are both in place; run it against the current branch state to confirm it passes only with the widened serializer.

- [ ] Write the parity test `tests/game_runtime/test_serialize_parity.py`. It runs a seeded mock-LLM (DemoAgent) game via the step-pump to a mid-game NIGHT position, snapshots the live `/state`, dumps the same engine's events to a temp `events.jsonl` + `roster.json`, reconstructs `/state` from disk, and asserts the load-bearing fields are equal:
```python
"""Spec §9 parity: live serialize_game_state /state == disk build_view /state mid-game."""

from __future__ import annotations

import json
import random

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.game_runtime.state.serialization import serialize_game_state
from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.interface.api.services.state import (
    build_state_from_snapshot,
    build_state_from_view,
)
from llm_werewolf.interface.api.services.view import build_view
from llm_werewolf.evaluation.post_game.event_adapter import event_to_dict


def _build_engine(seed: int) -> GameEngine:
    random.seed(seed)
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)
    engine.on_event = lambda _event: None
    players = [DemoAgent(name=f"P{i}", model="demo", seed=seed) for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)
    return engine


@pytest.mark.asyncio
async def test_live_state_matches_disk_state_midgame(tmp_path) -> None:
    engine = _build_engine(20260603)
    # Advance deterministically to DAY_DISCUSSION (round 1). With sheriff disabled the
    # step sequence is SETUP->NIGHT, NIGHT->DAY_DISCUSSION, so exactly 2 steps land here
    # with night deaths populated but voting NOT yet run (live votes empty). We stop
    # pre-voting on purpose: the disk fallback (view.py) never reconstructs a vote tally,
    # so tally parity is only meaningful where both sides are empty.
    for _ in range(2):
        assert not engine.is_over()
        await engine.step()
    assert engine.game_state.phase == GamePhase.DAY_DISCUSSION

    # Persist roster.json + events.jsonl exactly as the API disk sink would.
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    roster = {"players": [
        {"seat": int(p.player_id.rsplit("_", 1)[-1]), "player_id": p.player_id,
         "name": p.name, "role": p.get_role_name(), "camp": p.get_camp().value,
         "model": getattr(p, "ai_model", None)}
        for p in engine.game_state.players
    ]}
    (run_dir / "roster.json").write_text(json.dumps(roster, ensure_ascii=False), encoding="utf-8")
    rows = [event_to_dict(ev) for ev in engine.get_events()]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    # Live /state from the engine snapshot.
    snapshot = serialize_game_state(engine.game_state)
    camps = {p.player_id: p.get_camp().value for p in engine.game_state.players}
    live = build_state_from_snapshot(
        snapshot, status="running", error=None, cursor=len(rows), camps=camps)

    # Disk /state from the reconstructed view.
    view = build_view(run_dir, since=0, status="running", error=None)
    disk = build_state_from_view(view)

    # Field-for-field parity on everything build_view reconstructs.
    assert live.phase == disk.phase
    assert live.round == disk.round
    assert live.winner == disk.winner
    assert live.sheriff_seat == disk.sheriff_seat
    assert sorted(p.seat for p in live.players if p.is_alive) == \
        sorted(p.seat for p in disk.players if p.is_alive)
    assert sorted(p.seat for p in live.players if not p.is_alive) == \
        sorted(p.seat for p in disk.players if not p.is_alive)
    assert live.alive_count == disk.alive_count
    assert live.dead_count == disk.dead_count
    # votes: the disk fallback (view.py _build_snapshot) never reconstructs a vote tally,
    # so disk tally is always {}. We stopped at a pre-voting phase where the live tally is
    # also empty, making this parity meaningful rather than accidental.
    assert disk.votes.tally == {}
    assert live.votes.tally == {}
    # widened role_data (Hunter/Seer) is present on the live snapshot players
    for p in snapshot.players:
        if p.role_name in ("Hunter", "Seer"):
            assert set(p.role_data) >= {"ability_uses", "disabled"}
```

- [ ] Run it, verify it PASSES (it exercises already-implemented M1 composers + M3 widening end-to-end on a real seeded game):
```
uv run pytest tests/game_runtime/test_serialize_parity.py -v
```
Expected: `1 passed`. If the role_data assertion fails, M3 Task 9's widening did not land; if the alive/dead/sheriff/votes parity fails, the live and disk composers disagree and must be reconciled before M4 streams the contract.

- [ ] Commit:
```
git add tests/game_runtime/test_serialize_parity.py && git commit -m "Add §9 serialize_game_state vs build_view /state parity test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10 — Full milestone regression sweep

Run the engine/event/serialization test surface to confirm the new signals did not break existing behavior (event visibility defaults, action processing, serialization round-trips).

**Files** (none modified — verification task)

- [ ] Run the targeted suite for everything M3 touched:
```
uv run pytest tests/game_runtime/test_enums.py tests/game_runtime/test_event_visibility.py tests/game_runtime/test_events.py tests/game_runtime/test_action_processor.py tests/game_runtime/test_night_sub_phase_signals.py tests/game_runtime/test_phase_changed_signals.py tests/game_runtime/test_role_data_widening.py tests/game_runtime/test_serialize_parity.py tests/game_runtime/test_graveyard_and_wolf_team.py -v
```
Expected: all pass (no failures, no errors).

- [ ] Run the broader game_runtime suite to catch any consumer of the changed events/serialization:
```
uv run pytest tests/game_runtime -q
```
Expected: all pass. If a pre-existing test asserted one of the five skills logged `EventType.MESSAGE`, update that assertion to the new dedicated EventType (search for `white_wolf_kills`/`wolf_beauty_charms`/`nightmare_blocks`/`guardian_wolf_protected`/`raven_marks` in tests) and re-run.

- [ ] Commit any test fixups produced in the previous step (only if changes were needed):
```
git add tests/game_runtime && git commit -m "Update tests for typed skill events and widened role_data

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## M4 — EventHub (in-mem pub/sub) + SSE GET /stream with Last-Event-ID resume

**Coverage:** Covers spec §4 (EventHub component: 0-based monotonic seq, bounded per-subscriber asyncio.Queue, backfill from seq > Last-Event-ID, disk writer as parallel sink — one source two sinks), §5.2 (GET /games/{run_id}/stream SSE: id:<seq>, event: game, structured ViewEvent data payload incl. the five typed skill kinds + sub_phase via the widened view.py projection, heartbeat comment, Last-Event-ID resume), §5.1 (populate /state.sub_phase + current_actor_seat from the fan-out wrapper's session tracking), §8 (refresh/disconnect backfill from hub or, on eviction, the events.jsonl gap FIRST then in-buffer seqs; terminal type=system error event on engine error; EventSource auto-reconnect), §9 (EventHub tests: backfill exactness/order, two subscribers, disk still gets every event), §11 (SSE not buffered through proxy). M4 OWNS the SSE projection that reuses _map_event/_classify, so it widens view.py for M3's new EventTypes here (Task 4b). Builds on /state (M1), the step-pump/control gate (M2), and the engine signals (M3). Justifies SSE impl: plain StreamingResponse (no new direct pyproject dep) over sse-starlette.

**File structure:**

| File | Action | Responsibility |
|---|---|---|
| `src/llm_werewolf/interface/api/services/event_hub.py` | create | In-process pub/sub EventHub: assigns **0-based** monotonic seq (first event seq=0; next_seq = count = /view cursor), keeps a bounded ring buffer for backfill, exposes min_buffered_seq for eviction detection, fans out to per-subscriber bounded asyncio.Queue. backfill(after_seq) returns seq > after_seq (after_seq=-1 => all). Each buffered item carries (seq, raw_dict) where raw_dict = event_to_dict(event). |
| `src/llm_werewolf/interface/api/services/game_sessions.py` | modify | Add `hub: EventHub` + `current_sub_phase`/`current_actor_seat` fields to GameSession; add a session-aware fan-out on_event wrapper (Task 3) that writes events.jsonl (disk) AND session.hub.publish (in-mem) AND tracks sub_phase/current_actor_seat (Task 3b); wire it in _run_game; publish a terminal type=system error event then close the hub in the finally; read the tracking fields + gate/speed/captured last_night in get_state. Add get_session(run_id) accessor. |
| `src/llm_werewolf/interface/api/services/view.py` | modify | Task 4b: widen _SKILL_TYPES + _SKILL_KIND for M3's five typed skill EventTypes (guardian_wolf_guard etc.), add _SUB_PHASE_TYPES + a `sub_phase` classification, read actor_id (fallback player_id) in the skill branch, and emit ev.sub_phase. The same _map_event feeds /view, disk backfill, and the live SSE stream. |
| `src/llm_werewolf/interface/api/models/view.py` | modify | Task 4b: add "sub_phase" to ViewEventType and a `sub_phase: dict\|None` field to ViewEvent. |
| `src/llm_werewolf/interface/api/services/state.py` | modify | Task 3b: add sub_phase/current_actor_seat params to build_state_from_snapshot so get_state surfaces them on /state. |
| `src/llm_werewolf/interface/api/services/sse_stream.py` | create | SSE generator helpers: format_sse(seq, event_name, data_dict) frames `id:`/`event:`/`data:` (0-based seq); sse_event_payload(seq, raw_dict) reuses view._map_event; backfill_from_disk(run_dir, after_seq) reads events.jsonl using 0-based idx; stream_game(session, run_dir, last_event_id) async generator yielding the eviction-aware backfill (disk gap FIRST when Last-Event-ID is older than min_buffered_seq, then in-buffer seqs) + live + heartbeat comments. |
| `src/llm_werewolf/interface/api/routes/actions.py` | modify | Add GET /games/{run_id}/stream route returning StreamingResponse(media_type='text/event-stream') with no-buffering headers; reads Last-Event-ID header (fresh connection => after_seq=-1); backfills from hub (live session) or events.jsonl (evicted/finished), then streams live. |
| `tests/interface/test_view_service.py` | modify | Task 4b: assert the five new skill EventTypes classify as "skill" with the spec kinds and the SUB_PHASE event classifies as "sub_phase". |
| `tests/interface/test_event_hub.py` | create | Unit tests for EventHub: 0-based monotonic seq, two subscribers each get full stream, backfill returns exactly missed seqs in order (after_seq=-1 => all), ring-buffer eviction + min_buffered_seq, disk sink still receives every event via fan-out. |
| `tests/interface/test_sse_stream.py` | create | Unit tests: framing, ViewEvent payload, 0-based disk backfill, live backfill→stream, dedup, eviction→disk-gap fill (no silent gap), terminal type=system error frame. |
| `tests/interface/test_api_stream.py` | create | Integration tests for GET /stream via TestClient streaming: SSE framing (id/event/data, 0-based), Last-Event-ID backfill from disk for an evicted/finished run, heartbeat comment presence, no-buffering headers. |

**Goal:** Add an in-process `EventHub` fed by `on_event` (one source, two sinks: keep `IncrementalEventWriter` → `events.jsonl` AND publish to the hub with a monotonic `seq`). Add `GET /api/v1/games/{run_id}/stream` as Server-Sent Events with `id:<seq>`, `event: game`, and a JSON `data` payload (the structured `ViewEvent` shape from spec §5.2). Support reconnect via the `Last-Event-ID` header — backfill `seq > Last-Event-ID` from the hub, or from `events.jsonl` if the session was evicted, then stream live. Emit periodic heartbeat comments for idle phases.

**SSE implementation decision (justified):** Use FastAPI's plain `StreamingResponse(media_type="text/event-stream")` with a manual async generator, **not** `sse-starlette`. Rationale: (1) `sse-starlette` 3.4.4 is present in `uv.lock` only transitively and is **not** a declared direct dependency in `pyproject.toml` — adding it would be a new first-party dep for framing we can do in ~15 lines; YAGNI. (2) We need precise control over the `id:`/`event:`/`data:` frame and comment-only heartbeats, which a hand-rolled generator gives directly. (3) `StreamingResponse` is not buffered by Starlette/uvicorn; we additionally set `Cache-Control: no-cache`, `Connection: keep-alive`, and `X-Accel-Buffering: no` so the Vite dev proxy / any nginx in front does not buffer `text/event-stream` (spec §11). **No `pyproject.toml` change is required for this milestone.**

**Contract reuse:** the SSE `data` payload is the existing `ViewEvent` shape produced by `build_view._map_event(seq, row)` (`interface/api/services/view.py:95`), so the stream and the disk/`/view` projections agree field-for-field. The on-disk row used both as the disk sink and as the hub payload is exactly `event_to_dict(event)` (`evaluation/post_game/event_adapter.py:13`).

**Seq numbering is 0-BASED everywhere** to match `build_view`: it maps each event with `_map_event(idx, row)` so the **first event has seq=0** and `cursor=len(rows)` (`view.py:179,181`). Therefore the EventHub assigns `seq = 0`-based position (first published event seq=0; `next_seq`/cursor = count of events), the SSE `id:` is that 0-based `seq`, `backfill_from_disk` uses the 0-based line index `idx` (NOT `idx+1`), and a `Last-Event-ID` of N backfills events with `seq > N`. A fresh connection (no `Last-Event-ID`) uses `after_seq = -1` so seq 0 is included. This keeps `/view` per-event seq, `/state.cursor`, and `/stream` `Last-Event-ID` all aligned on the same 0-based axis.

---

### Task 1 — `EventHub`: monotonic seq + ring buffer + backfill

**Files**
- Create: `src/llm_werewolf/interface/api/services/event_hub.py`
- Test: `tests/interface/test_event_hub.py`

- [ ] Write the failing test for monotonic seq + backfill exactness:

```python
# tests/interface/test_event_hub.py
"""Unit tests for the in-process EventHub (pub/sub + backfill)."""

from __future__ import annotations

from llm_werewolf.interface.api.services.event_hub import EventHub


def test_publish_assigns_zero_based_monotonic_seq() -> None:
    # 0-based to match build_view: first event seq=0, cursor=len(rows).
    hub = EventHub(buffer_size=128)
    assert hub.publish({"event_type": "game_started"}) == 0
    assert hub.publish({"event_type": "phase_changed"}) == 1
    assert hub.publish({"event_type": "player_speech"}) == 2
    # next_seq (== count of events published == /view cursor) is 3 after 3 publishes
    assert hub.next_seq == 3


def test_backfill_returns_only_missed_seqs_in_order() -> None:
    hub = EventHub(buffer_size=128)
    for i in range(5):  # seqs 0..4
        hub.publish({"event_type": "player_speech", "data": {"i": i}})
    # Last-Event-ID = 2 means the client has seen seq 0,1,2; backfill seq > 2.
    missed = hub.backfill(after_seq=2)
    assert [seq for seq, _ in missed] == [3, 4]
    assert [row["data"]["i"] for _, row in missed] == [3, 4]


def test_backfill_from_negative_one_returns_all() -> None:
    # A fresh connection (no Last-Event-ID) uses after_seq=-1 to get seq >= 0.
    hub = EventHub(buffer_size=128)
    for i in range(3):  # seqs 0..2
        hub.publish({"event_type": "player_speech", "data": {"i": i}})
    missed = hub.backfill(after_seq=-1)
    assert [seq for seq, _ in missed] == [0, 1, 2]


def test_backfill_after_current_is_empty() -> None:
    hub = EventHub(buffer_size=128)
    hub.publish({"event_type": "game_started"})  # seq 0
    assert hub.backfill(after_seq=10) == []


def test_ring_buffer_evicts_oldest() -> None:
    hub = EventHub(buffer_size=3)
    for i in range(5):  # seqs 0..4, only last 3 (2,3,4) retained
        hub.publish({"event_type": "player_speech", "data": {"i": i}})
    missed = hub.backfill(after_seq=-1)
    assert [seq for seq, _ in missed] == [2, 3, 4]
    # The minimum seq still buffered is exposed for the disk-fallback gap check.
    assert hub.min_buffered_seq == 2
```

- [ ] Run it, verify it FAILS (module does not exist yet):

```
uv run pytest tests/interface/test_event_hub.py -v
```

Expected: `ModuleNotFoundError: No module named 'llm_werewolf.interface.api.services.event_hub'` → all 5 tests ERROR/FAIL.

- [ ] Write the minimal implementation:

```python
# src/llm_werewolf/interface/api/services/event_hub.py
"""In-process publish/subscribe hub for live engine events.

One source (engine.on_event) fans out to two sinks: the disk writer
(events.jsonl, unchanged) and this hub. The hub assigns a monotonic
``seq`` to every event, keeps a bounded ring buffer so reconnecting SSE
clients can backfill ``seq > Last-Event-ID``, and pushes each event to a
bounded per-subscriber queue.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel pushed to every subscriber queue when the stream is closed.
_CLOSED = object()


class EventHub:
    """Per-run in-memory event bus with seq numbering and backfill."""

    def __init__(self, buffer_size: int = 4096, queue_size: int = 1024) -> None:
        self._buffer: deque[tuple[int, dict[str, Any]]] = deque(maxlen=buffer_size)
        self._subscribers: list[asyncio.Queue[Any]] = []
        # 0-based: the seq to assign to the NEXT published event. After N
        # publishes this equals N, matching build_view's cursor=len(rows).
        self._next_seq = 0
        self._queue_size = queue_size
        self._closed = False

    @property
    def next_seq(self) -> int:
        """The seq the next published event will get (== count published == /view cursor)."""
        return self._next_seq

    @property
    def min_buffered_seq(self) -> int | None:
        """Smallest seq still in the ring buffer, or None when empty.

        Used by the stream route to detect that a requested Last-Event-ID is
        older than the buffer (evicted) so it must backfill from events.jsonl.
        """
        return self._buffer[0][0] if self._buffer else None

    def publish(self, row: dict[str, Any]) -> int:
        """Assign the next 0-based seq, buffer the row, fan it out. Returns the seq."""
        seq = self._next_seq
        self._next_seq += 1
        item = (seq, row)
        self._buffer.append(item)
        for queue in self._subscribers:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                logger.warning("EventHub subscriber queue full; dropping seq=%s", seq)
        return seq

    def backfill(self, after_seq: int) -> list[tuple[int, dict[str, Any]]]:
        """Return buffered (seq, row) with seq > after_seq, in seq order.

        A fresh connection passes after_seq=-1 to get every buffered event
        (seq >= 0); Last-Event-ID=N passes after_seq=N to resume after seq N.
        """
        return [item for item in self._buffer if item[0] > after_seq]

    def subscribe(self) -> asyncio.Queue[Any]:
        """Register a new live subscriber queue."""
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.append(queue)
        if self._closed:
            queue.put_nowait(_CLOSED)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Any]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def close(self) -> None:
        """Signal end-of-stream to all current subscribers."""
        self._closed = True
        for queue in self._subscribers:
            try:
                queue.put_nowait(_CLOSED)
            except asyncio.QueueFull:
                pass

    @property
    def closed(self) -> bool:
        return self._closed
```

- [ ] Run the test, verify it PASSES:

```
uv run pytest tests/interface/test_event_hub.py -v
```

Expected: `test_publish_assigns_zero_based_monotonic_seq PASSED`, `test_backfill_returns_only_missed_seqs_in_order PASSED`, `test_backfill_from_negative_one_returns_all PASSED`, `test_backfill_after_current_is_empty PASSED`, `test_ring_buffer_evicts_oldest PASSED` — 5 passed.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/event_hub.py tests/interface/test_event_hub.py && git commit -m "feat(api): in-process EventHub with monotonic seq + ring-buffer backfill

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2 — `EventHub` live subscribe + close (async pub/sub) — added edge-case coverage

**Files**
- Modify: `tests/interface/test_event_hub.py`
- (no implementation change — `subscribe`/`close` are already written in Task 1. This task is NOT a red-first TDD cycle: it adds **edge-case coverage** of already-implemented behavior — concurrent fan-out to two subscribers, the close sentinel, and subscribe-after-close. The genuine red-first cycle for the hub lives in Task 1; these tests are expected to pass on first run against the Task 1 impl.)

- [ ] Append the edge-case coverage tests (they exercise async behavior Task 1 implemented but did not assert):

```python
# tests/interface/test_event_hub.py  (append)
from llm_werewolf.interface.api.services.event_hub import EventHub, _CLOSED


async def test_two_subscribers_each_get_full_live_stream() -> None:
    hub = EventHub()
    q1 = hub.subscribe()
    q2 = hub.subscribe()
    hub.publish({"event_type": "a"})  # seq 0
    hub.publish({"event_type": "b"})  # seq 1
    got1 = [await q1.get(), await q1.get()]
    got2 = [await q2.get(), await q2.get()]
    assert [seq for seq, _ in got1] == [0, 1]
    assert [seq for seq, _ in got2] == [0, 1]
    assert [row["event_type"] for _, row in got1] == ["a", "b"]


async def test_close_pushes_sentinel_to_subscribers() -> None:
    hub = EventHub()
    q = hub.subscribe()
    hub.publish({"event_type": "a"})  # seq 0
    hub.close()
    assert (await q.get())[1]["event_type"] == "a"
    assert await q.get() is _CLOSED
    assert hub.closed is True


async def test_subscribe_after_close_gets_sentinel_immediately() -> None:
    hub = EventHub()
    hub.close()
    q = hub.subscribe()
    assert await q.get() is _CLOSED
```

- [ ] Run, verify the new tests PASS (impl already exists; this is coverage, not a red cycle):

```
uv run pytest tests/interface/test_event_hub.py -v
```

Expected: 8 passed (5 from Task 1 + 3 new). `asyncio_mode = "auto"` (pyproject.toml:36) runs the `async def` tests without a marker.

- [ ] Commit:

```
git add tests/interface/test_event_hub.py && git commit -m "test(api): lock EventHub live subscribe + close-sentinel behavior

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3 — Fan-out `on_event` (disk + hub) wired into `GameSession`

**Files**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_api_services.py`

- [ ] Write the failing test (fan-out hits both sinks; `seq` is assigned by the hub):

```python
# tests/interface/test_api_services.py  (append)
import json as _json

from llm_werewolf.interface.api.services.event_hub import EventHub
from llm_werewolf.interface.api.services.game_sessions import (
    GameSession,
    GameSessionStatus,
    IncrementalEventWriter,
    make_fanout_on_event,
)


class _StubEvent:
    """Minimal stand-in for game_runtime Event accepted by event_to_dict."""

    def __init__(self, etype: str) -> None:
        from datetime import datetime

        from llm_werewolf.game_runtime.types.enums import EventType, GamePhase

        self.event_type = EventType(etype)
        self.timestamp = datetime.now()
        self.round_number = 1
        self.phase = GamePhase.DAY_DISCUSSION
        self.message = "P1: hi"
        self.data = {"player_id": "player_1", "player_name": "P1", "speech": "hi"}
        self.visible_to = None


def test_fanout_writes_disk_and_publishes_to_hub(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    session = GameSession(
        run_id="r", run_dir=run_dir,
        config_path=tmp_path / "c.yaml", config_id="c",
    )
    writer = IncrementalEventWriter(run_dir)
    on_event = make_fanout_on_event(writer, session)

    on_event(_StubEvent("player_speech"))
    on_event(_StubEvent("phase_changed"))

    # disk sink received both rows
    lines = (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert _json.loads(lines[0])["event_type"] == "player_speech"

    # hub sink assigned 0-based monotonic seqs and buffered both rows
    assert session.hub.next_seq == 2          # two events published -> next seq is 2
    backfilled = session.hub.backfill(after_seq=-1)   # -1 => all seqs >= 0
    assert [seq for seq, _ in backfilled] == [0, 1]
    assert backfilled[0][1]["event_type"] == "player_speech"


def test_game_session_has_hub_field() -> None:
    session = GameSession(
        run_id="r", run_dir=__import__("pathlib").Path("."),
        config_path=__import__("pathlib").Path("."), config_id="c",
    )
    assert isinstance(session.hub, EventHub)
    assert session.status is GameSessionStatus.PENDING
```

- [ ] Run, verify it FAILS:

```
uv run pytest tests/interface/test_api_services.py::test_fanout_writes_disk_and_publishes_to_hub tests/interface/test_api_services.py::test_game_session_has_hub_field -v
```

Expected: `ImportError: cannot import name 'make_fanout_on_event'` and `AttributeError: 'GameSession' object has no attribute 'hub'` → both FAIL.

- [ ] Add the `hub` field to `GameSession` (after `human_seats`, `game_sessions.py:115`):

```python
    human_seats: list[int] = field(default_factory=list)
    hub: "EventHub" = field(default_factory=lambda: EventHub())
```

- [ ] Add the `EventHub` import near the other service imports (after `game_sessions.py:34`, the `extract_game_snapshot` import):

```python
from llm_werewolf.interface.api.services.event_hub import EventHub
```

- [ ] Add the fan-out factory just below the `IncrementalEventWriter` class (after `game_sessions.py:127`). It takes the `GameSession` (not just the hub) so the same wrapper that sees every event can also track `/state.sub_phase` / `current_actor_seat` in Task 3b:

```python
def make_fanout_on_event(
    writer: IncrementalEventWriter, session: "GameSession"
) -> Callable[[object], None]:
    """One source, two sinks: append to events.jsonl AND publish to the hub.

    The same ``event_to_dict`` row is used for both so the hub seq stays
    aligned with the events.jsonl line index (the 0-based /view cursor).
    """

    def _fanout(event: object) -> None:
        row = event_to_dict(event)
        writer._write_row(row)
        session.hub.publish(row)

    return _fanout
```

- [ ] Refactor `IncrementalEventWriter.__call__` to share row-building (avoid double `event_to_dict`); replace `game_sessions.py:125-127`:

```python
    def __call__(self, event: object) -> None:
        self._write_row(event_to_dict(event))

    def _write_row(self, row: dict) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
```

- [ ] Add the `Callable` import to the typing line (`game_sessions.py:12`):

```python
from typing import TYPE_CHECKING, Any, Callable
```

- [ ] Wire the fan-out in `_run_game`; replace `game_sessions.py:245-246`:

```python
            writer = IncrementalEventWriter(session.run_dir)
            engine.on_event = make_fanout_on_event(writer, session)
```

- [ ] Publish a terminal `system` error event (spec §8) then close the hub so live SSE subscribers receive the error and then terminate; in `_run_game`'s `finally` block add before `session.completed_at = ...` (`game_sessions.py:272-274`). The existing `except Exception` arm already sets `session.error = str(exc)` (verified `game_sessions.py:268-271`):

```python
        finally:
            if session.error and session.status is GameSessionStatus.FAILED:
                # Spec §8: terminal type=system error event onto the hub BEFORE close,
                # so connected SSE clients (and hub-backfill reconnects) receive it.
                session.hub.publish({
                    "event_type": "system",
                    "round_number": 0,
                    "phase": "ended",
                    "message": session.error,
                    "data": {"error": session.error},
                })
            session.hub.close()
            session.completed_at = datetime.now().isoformat(timespec="seconds")
            self._write_meta(session)
```

- [ ] Run, verify it PASSES:

```
uv run pytest tests/interface/test_api_services.py::test_fanout_writes_disk_and_publishes_to_hub tests/interface/test_api_services.py::test_game_session_has_hub_field -v
```

Expected: 2 passed.

- [ ] Run the existing service + action tests to confirm no regression (disk format unchanged):

```
uv run pytest tests/interface/test_api_services.py tests/interface/test_api_actions.py -v
```

Expected: all previously-passing tests still pass (e.g. `test_view_endpoint_returns_projection PASSED`).

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_services.py && git commit -m "feat(api): fan-out on_event to events.jsonl + EventHub (one source, two sinks)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3b — Track `sub_phase` + `current_actor_seat` on the session and surface them on `/state`

**Files**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Modify: `src/llm_werewolf/interface/api/services/state.py`
- Test: `tests/interface/test_api_services.py`
- Test: `tests/interface/test_api_control.py` (extend)

Spec §5.1 requires `/state.sub_phase` and `/state.current_actor_seat`, but `serialize_game_state` does NOT carry them (verified: `state/serialization.py:154-192` has no such fields) — they are transient *stream signals*. The fan-out wrapper from Task 3 sees **every** event, so it is the natural place to maintain them on the session: a `SUB_PHASE` event sets `session.current_sub_phase = data["name"]`; a player speech / `role_acting` event sets `session.current_actor_seat = seat`; a `phase_changed` event clears `current_sub_phase` (a new GamePhase ends any night sub-phase). M1's `get_state` then reads these optional session fields into `/state` (null-safe).

- [ ] Write the failing tracking test. Append to `tests/interface/test_api_services.py`:
```python
def test_fanout_tracks_sub_phase_and_actor_seat(tmp_path) -> None:
    run_dir = tmp_path / "run2"
    run_dir.mkdir()
    session = GameSession(
        run_id="r2", run_dir=run_dir,
        config_path=tmp_path / "c.yaml", config_id="c",
    )
    on_event = make_fanout_on_event(IncrementalEventWriter(run_dir), session)

    # defaults
    assert session.current_sub_phase is None
    assert session.current_actor_seat is None

    sub = _StubEvent("sub_phase")
    sub.data = {"name": "werewolf_chat"}
    on_event(sub)
    assert session.current_sub_phase == "werewolf_chat"

    speech = _StubEvent("player_speech")
    speech.data = {"player_id": "player_4", "player_name": "P4", "speech": "hi"}
    on_event(speech)
    assert session.current_actor_seat == 4

    phase = _StubEvent("phase_changed")
    phase.data = {}
    on_event(phase)
    assert session.current_sub_phase is None   # a new GamePhase clears the sub-phase
```
(Allow `_StubEvent` to accept any `EventType` value — `sub_phase` requires M3's enum member; if M3 has not landed in this branch, construct the stub with a raw object whose `.event_type.value == "sub_phase"` instead.)

- [ ] Run, verify it FAILS:
```
uv run pytest tests/interface/test_api_services.py::test_fanout_tracks_sub_phase_and_actor_seat -v
```
Expected: `AttributeError: 'GameSession' object has no attribute 'current_sub_phase'`.

- [ ] Add the two tracking fields to `GameSession` (after `hub`, near `game_sessions.py:115`):
```python
    hub: "EventHub" = field(default_factory=lambda: EventHub())
    current_sub_phase: str | None = None
    current_actor_seat: int | None = None
```

- [ ] Update the fan-out wrapper to maintain them. In `make_fanout_on_event`'s `_fanout`, after `session.hub.publish(row)`, add the tracking:
```python
    def _fanout(event: object) -> None:
        row = event_to_dict(event)
        writer._write_row(row)
        session.hub.publish(row)
        _track_phase_signals(session, row)
```
Add the helper as a module-level function next to `make_fanout_on_event`:
```python
_SPEECH_EVENT_TYPES = {"player_speech", "player_discussion", "role_acting"}


def _track_phase_signals(session: "GameSession", row: dict) -> None:
    """Maintain session.current_sub_phase / current_actor_seat from the event stream."""
    etype = str(row.get("event_type", ""))
    data = row.get("data") or {}
    if etype == "sub_phase":
        session.current_sub_phase = data.get("name")
    elif etype == "phase_changed":
        session.current_sub_phase = None  # a new GamePhase ends any night sub-phase
    if etype in _SPEECH_EVENT_TYPES:
        seat = _seat_of(str(data.get("player_id") or ""))
        if seat is not None:
            session.current_actor_seat = seat
```
(`_seat_of` already exists from M2 Task 2; reuse it.)

- [ ] Add `sub_phase` + `current_actor_seat` params to `build_state_from_snapshot` so `get_state` can pass the session fields. In `src/llm_werewolf/interface/api/services/state.py`, extend the signature (alongside the M2 Task 6 additions) with:
```python
      sub_phase: str | None = None
      current_actor_seat: int | None = None
```
and pass them into the `return GameStateResponse(...)`:
```python
          sub_phase=sub_phase,
          current_actor_seat=current_actor_seat,
```

- [ ] Read the session fields in `get_state`'s live branch. In `GameSessionManager.get_state` (M1, live branch), pass the new keywords into the `build_state_from_snapshot(...)` call added in M2 Task 6:
```python
                      sub_phase=session.current_sub_phase,
                      current_actor_seat=session.current_actor_seat,
```

- [ ] Write the `/state` surfacing test. Append to `tests/interface/test_api_control.py`:
```python
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
```

- [ ] Run, verify both PASS:
```
uv run pytest tests/interface/test_api_services.py::test_fanout_tracks_sub_phase_and_actor_seat tests/interface/test_api_control.py::test_state_surfaces_sub_phase_and_actor_seat -v
```
Expected: 2 passed — the fan-out maintains the session fields and `/state` surfaces them (null when never set).

- [ ] Commit:
```
git add src/llm_werewolf/interface/api/services/game_sessions.py src/llm_werewolf/interface/api/services/state.py tests/interface/test_api_services.py tests/interface/test_api_control.py && git commit -m "feat(api): track sub_phase + current_actor_seat and surface on /state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4 — `GameSessionManager.get_session` accessor

**Files**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_api_services.py`

- [ ] Write the failing test:

```python
# tests/interface/test_api_services.py  (append)
from llm_werewolf.interface.api.services.game_sessions import game_session_manager


def test_get_session_returns_registered_and_none() -> None:
    game_session_manager.reset()
    assert game_session_manager.get_session("nope") is None
    session = GameSession(
        run_id="abc", run_dir=__import__("pathlib").Path("."),
        config_path=__import__("pathlib").Path("."), config_id="c",
    )
    game_session_manager._sessions["abc"] = session
    assert game_session_manager.get_session("abc") is session
    game_session_manager.reset()
```

- [ ] Run, verify it FAILS:

```
uv run pytest tests/interface/test_api_services.py::test_get_session_returns_registered_and_none -v
```

Expected: `AttributeError: 'GameSessionManager' object has no attribute 'get_session'` → FAIL.

- [ ] Add the accessor to `GameSessionManager` (after `reset`, `game_sessions.py:138`):

```python
    def get_session(self, run_id: str) -> GameSession | None:
        return self._sessions.get(run_id)
```

- [ ] Run, verify it PASSES:

```
uv run pytest tests/interface/test_api_services.py::test_get_session_returns_registered_and_none -v
```

Expected: 1 passed.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_services.py && git commit -m "feat(api): GameSessionManager.get_session accessor for the stream route

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4b — Extend `view.py` projection to recognize M3's new EventTypes (skills + sub_phase)

**Files**
- Modify: `src/llm_werewolf/interface/api/services/view.py`
- Test: `tests/interface/test_view_service.py`

The SSE `data` payload (Task 5 onward) reuses `build_view._map_event`/`_classify` UNCHANGED. But M3 added five typed skill EventTypes and a `SUB_PHASE` EventType that `view.py` does not yet know about — so they would be misclassified as `"system"` and the structured `skill`/`sub_phase` payloads spec §5.2 mandates (and M5's sub-phase highlight depends on) would never reach the stream. This task widens the projection so the same `_map_event` that feeds `/view`, the disk backfill, AND the live SSE stream emits the correct `type`/`kind`.

Verified against the current source (`interface/api/services/view.py`): `_SKILL_TYPES` (line 16) and `_SKILL_KIND` (line 31) are module-level sets/dicts; `_classify` (line 65) returns `"skill"` for `_SKILL_TYPES` and `"phase"` for `_PHASE_TYPES`; `_map_event` (line 95) builds `ev.skill = {kind, actor{seat}, target{seat}, result}` reading `data.get("player_id")` (actor) and `data.get("target_id")` (target). M3 Task 3's typed skill events carry `actor_id`/`target_id`/`result`, so the skill branch must read `actor_id` (falling back to `player_id` for the old events).

> **Skill `kind` strings MUST match spec §5.2 / the frontend `SkillKind`** — note `guardian_wolf_guard` (NOT `guardian_wolf_protected`): `white_wolf_killed`→`white_wolf_kill`, `wolf_beauty_charmed`→`wolf_beauty_charm`, `nightmare_blocked`→`nightmare_block`, `guardian_wolf_protected`→`guardian_wolf_guard`, `raven_marked`→`raven_mark`.

- [ ] Write the failing tests. Append to `tests/interface/test_view_service.py`:
```python
from llm_werewolf.interface.api.services.view import _classify, _map_event


def test_new_skill_eventtypes_classify_as_skill_with_spec_kind() -> None:
    cases = {
        "white_wolf_killed": "white_wolf_kill",
        "wolf_beauty_charmed": "wolf_beauty_charm",
        "nightmare_blocked": "nightmare_block",
        "guardian_wolf_protected": "guardian_wolf_guard",
        "raven_marked": "raven_mark",
    }
    for event_type, expected_kind in cases.items():
        assert _classify(event_type) == "skill", event_type
        row = {
            "event_type": event_type, "round_number": 1, "phase": "night",
            "message": "", "data": {"actor_id": "player_2", "target_id": "player_5",
                                    "result": "ok"},
        }
        ev = _map_event(3, row)
        assert ev.type == "skill"
        assert ev.skill["kind"] == expected_kind
        assert ev.skill["actor"] == {"seat": 2}
        assert ev.skill["target"] == {"seat": 5}
        assert ev.skill["result"] == "ok"


def test_sub_phase_eventtype_classifies_as_sub_phase() -> None:
    assert _classify("sub_phase") == "sub_phase"
    row = {"event_type": "sub_phase", "round_number": 1, "phase": "night",
           "message": "", "data": {"name": "werewolf_chat"}}
    ev = _map_event(4, row)
    assert ev.type == "sub_phase"
    assert ev.sub_phase == {"name": "werewolf_chat"}
    # a night-phase sub_phase is a public display hint, not god-only
    assert ev.reveal == "now"
    assert ev.visibility == "public"
```

- [ ] Run, verify it FAILS:
```
uv run pytest tests/interface/test_view_service.py::test_new_skill_eventtypes_classify_as_skill_with_spec_kind tests/interface/test_view_service.py::test_sub_phase_eventtype_classifies_as_sub_phase -v
```
Expected: both FAIL — the new EventTypes are not in `_SKILL_TYPES`/`_SKILL_KIND` so `_classify` returns `"system"`; `_classify("sub_phase")` returns `"system"` (not `"sub_phase"`); `ev.sub_phase` does not exist yet.

- [ ] Extend `_SKILL_TYPES` in `src/llm_werewolf/interface/api/services/view.py` (line 16) to include the five new members:
```python
_SKILL_TYPES = {
    "werewolf_killed", "witch_saved", "witch_poisoned", "seer_checked",
    "guard_protected", "graveyard_keeper_check", "hunter_revenge",
    "sheriff_badge_transferred", "role_acting",
    "white_wolf_killed", "wolf_beauty_charmed", "nightmare_blocked",
    "guardian_wolf_protected", "raven_marked",
}
```

- [ ] Extend `_SKILL_KIND` (line 31) with the spec §5.2 kind strings (note `guardian_wolf_guard`):
```python
_SKILL_KIND = {
    "werewolf_killed": "wolf_kill", "witch_saved": "witch_save",
    "witch_poisoned": "witch_poison", "seer_checked": "seer_check",
    "guard_protected": "guard", "hunter_revenge": "hunter_shoot",
    "sheriff_badge_transferred": "badge_transfer",
    "white_wolf_killed": "white_wolf_kill",
    "wolf_beauty_charmed": "wolf_beauty_charm",
    "nightmare_blocked": "nightmare_block",
    "guardian_wolf_protected": "guardian_wolf_guard",
    "raven_marked": "raven_mark",
}
```

- [ ] Add the `sub_phase` set + classification. After the `_PHASE_TYPES` definition (line 21) add:
```python
_SUB_PHASE_TYPES = {"sub_phase"}
```
In `_classify` (line 65), add a branch for it — insert immediately after the `_PHASE_TYPES` branch:
```python
    if event_type in _SUB_PHASE_TYPES:
        return "sub_phase"
```

- [ ] Keep `sub_phase` PUBLIC/now (it is a display hint, spec §5.2). Without this, `_reveal_visibility` would hide it as `("on_game_end", "god")` because sub_phase events occur during `night` (a `_NIGHT_PHASES` phase, so the night branch is taken and the inner speech/vote/death check fails). In `_reveal_visibility` (line 83), add a guard immediately after the `_PUBLIC_SKILLS` check, before the night branch:
```python
    if ui == "sub_phase":
        return "now", "public"
```
(Scoped to `sub_phase` only — existing `phase`/skill/etc. visibility behavior is unchanged so no existing `test_view_service.py` assertion regresses. Verify after editing that `_map_event(seq, {"event_type":"sub_phase","phase":"night",...}).visibility == "public"` and `.reveal == "now"`.)

- [ ] Make the skill branch read `actor_id` (new events) with a `player_id` fallback (old events), and add a `sub_phase` branch in `_map_event`. Change the skill branch (line 110-116):
```python
    elif ui == "skill":
        ev.skill = {
            "kind": _SKILL_KIND.get(event_type, event_type),
            "actor": {"seat": _seat_of(data.get("actor_id") or data.get("player_id"))},
            "target": {"seat": _seat_of(data.get("target_id"))},
            "result": data.get("result"),
        }
    elif ui == "sub_phase":
        ev.sub_phase = {"name": data.get("name")}
```

- [ ] Add `"sub_phase"` to the `ViewEventType` Literal and a `sub_phase` field to `ViewEvent`. In `src/llm_werewolf/interface/api/models/view.py`, change the `ViewEventType` Literal (line 11-13) to include `"sub_phase"`:
```python
ViewEventType = Literal[
    "speech", "skill", "vote", "death", "phase", "sub_phase",
    "system", "belief", "vote_intention",
]
```
and add the field to `ViewEvent` (line 51, right after `death`), mirroring the existing optional-structure style (`dict[str, Any] | None = None`):
```python
    death: dict[str, Any] | None = None
    sub_phase: dict[str, Any] | None = None
```

- [ ] Run, verify it PASSES:
```
uv run pytest tests/interface/test_view_service.py -v
```
Expected: the two new tests pass and all existing `test_view_service.py` tests still pass (the additions are additive — old EventTypes keep their kinds).

- [ ] Commit:
```
git add src/llm_werewolf/interface/api/services/view.py src/llm_werewolf/interface/api/models/view.py tests/interface/test_view_service.py && git commit -m "feat(api): classify M3 typed skill + sub_phase events in view projection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5 — SSE framing + payload helpers (reuse `_map_event`)

**Files**
- Create: `src/llm_werewolf/interface/api/services/sse_stream.py`
- Test: `tests/interface/test_sse_stream.py`

- [ ] Write the failing test for framing + payload + disk backfill:

```python
# tests/interface/test_sse_stream.py
"""Unit tests for SSE framing + payload + disk backfill helpers."""

from __future__ import annotations

import json

from llm_werewolf.interface.api.services.sse_stream import (
    backfill_from_disk,
    format_sse,
    sse_event_payload,
)


def test_format_sse_frames_id_event_data() -> None:
    frame = format_sse(143, "game", {"seq": 143, "type": "speech"})
    assert frame.startswith("id: 143\n")
    assert "event: game\n" in frame
    assert 'data: {"seq": 143, "type": "speech"}\n' in frame
    assert frame.endswith("\n\n")


def test_sse_event_payload_uses_view_mapping() -> None:
    row = {
        "event_type": "player_speech", "round_number": 2, "phase": "day_discussion",
        "message": "P3: hi",
        "data": {"player_id": "player_3", "player_name": "P3", "speech": "hi",
                 "private_thought": "hmm"},
    }
    payload = sse_event_payload(7, row)
    assert payload["seq"] == 7
    assert payload["type"] == "speech"
    assert payload["phase"] == "day_discussion"
    assert payload["speaker"] == {"seat": 3, "name": "P3"}
    assert payload["public_text"] == "hi"
    assert payload["private_thought"] == "hmm"
    assert payload["reveal"] == "now"
    assert payload["visibility"] == "public"


def test_sse_payload_for_five_typed_skills_has_type_skill_and_spec_kind() -> None:
    # Depends on Task 4b widening view._SKILL_TYPES/_SKILL_KIND.
    cases = {
        "white_wolf_killed": "white_wolf_kill",
        "wolf_beauty_charmed": "wolf_beauty_charm",
        "nightmare_blocked": "nightmare_block",
        "guardian_wolf_protected": "guardian_wolf_guard",
        "raven_marked": "raven_mark",
    }
    for event_type, expected_kind in cases.items():
        row = {"event_type": event_type, "round_number": 1, "phase": "night",
               "message": "", "data": {"actor_id": "player_2", "target_id": "player_5",
                                       "result": "ok"}}
        payload = sse_event_payload(9, row)
        assert payload["type"] == "skill", event_type
        assert payload["skill"]["kind"] == expected_kind


def test_sse_payload_for_sub_phase_has_type_sub_phase() -> None:
    row = {"event_type": "sub_phase", "round_number": 1, "phase": "night",
           "message": "", "data": {"name": "witch_decide"}}
    payload = sse_event_payload(10, row)
    assert payload["type"] == "sub_phase"
    assert payload["sub_phase"] == {"name": "witch_decide"}


def test_backfill_from_disk_returns_seqs_after_cursor(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rows = [
        {"event_type": "game_started", "round_number": 0, "phase": "setup", "message": "", "data": {}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P1: a", "data": {"player_id": "player_1", "player_name": "P1", "speech": "a"}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P2: b", "data": {"player_id": "player_2", "player_name": "P2", "speech": "b"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    # 0-based seqs: rows are seq 0,1,2. Last-Event-ID=0 => backfill seq > 0.
    missed = backfill_from_disk(run_dir, after_seq=0)
    assert [seq for seq, _ in missed] == [1, 2]
    assert missed[0][1]["data"]["player_name"] == "P1"
```

- [ ] Run, verify it FAILS:

```
uv run pytest tests/interface/test_sse_stream.py -v
```

Expected: `ModuleNotFoundError: No module named 'llm_werewolf.interface.api.services.sse_stream'` → all FAIL.

- [ ] Write the implementation:

```python
# src/llm_werewolf/interface/api/services/sse_stream.py
"""Server-Sent Events helpers for GET /games/{run_id}/stream.

Plain StreamingResponse framing (no sse-starlette dependency): each event is
`id: <seq>` / `event: game` / `data: <ViewEvent JSON>`. The JSON payload reuses
build_view._map_event so the stream agrees field-for-field with /view and disk.
A comment-only heartbeat (`: keep-alive`) keeps idle connections open.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from llm_werewolf.interface.api.services.event_hub import _CLOSED
from llm_werewolf.interface.api.services.view import _map_event, _read_jsonl

if TYPE_CHECKING:
    from llm_werewolf.interface.api.services.game_sessions import GameSession

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 15.0


def sse_event_payload(seq: int, row: dict[str, Any]) -> dict[str, Any]:
    """Build the structured ViewEvent dict carried in the SSE `data` field."""
    return _map_event(seq, row).model_dump()


def format_sse(seq: int, event_name: str, data: dict[str, Any]) -> str:
    """Frame one SSE message: id / event / data (JSON), terminated by a blank line."""
    body = json.dumps(data, ensure_ascii=False)
    return f"id: {seq}\nevent: {event_name}\ndata: {body}\n\n"


def format_heartbeat() -> str:
    """Comment-only frame to keep the connection alive through idle phases."""
    return ": keep-alive\n\n"


def backfill_from_disk(run_dir: Path, after_seq: int) -> list[tuple[int, dict[str, Any]]]:
    """Reconstruct (seq, row) pairs from events.jsonl for evicted/finished runs.

    seq is the 0-based line index, matching the hub's 0-based seq and
    build_view's per-event seq (`_map_event(idx, row)`) / cursor (`len(rows)`).
    A fresh connection passes after_seq=-1 to get every row (seq >= 0).
    """
    rows = _read_jsonl(run_dir / "events.jsonl")
    return [(idx, row) for idx, row in enumerate(rows) if idx > after_seq]


async def stream_game(
    *, session: "GameSession | None", run_dir: Path, last_event_id: int
) -> AsyncIterator[str]:
    """Yield SSE frames: backfill (seq > last_event_id) then live, with heartbeats.

    Live session → backfill the missed gap (from events.jsonl FIRST if the
    requested cursor was evicted from the hub's bounded buffer, then from the
    in-buffer seqs), then drain the subscriber queue. On engine error the run
    publishes a terminal type=system error event onto the hub (Task 3 finally
    block) BEFORE closing, so it flows through the live queue / backfill like any
    other event — no special synthesis needed here. Evicted/finished run
    (session is None) → backfill entirely from events.jsonl.
    """
    if session is None:
        for seq, row in backfill_from_disk(run_dir, last_event_id):
            yield format_sse(seq, "game", sse_event_payload(seq, row))
        return

    hub = session.hub
    queue = hub.subscribe()
    try:
        backfilled_through = last_event_id
        # Spec §8: if the requested Last-Event-ID is older than the oldest seq
        # still in the hub's bounded buffer, those seqs were EVICTED. Backfill
        # the missing gap from events.jsonl FIRST, then the in-buffer seqs.
        min_buffered = hub.min_buffered_seq
        if min_buffered is not None and last_event_id < min_buffered - 1:
            # Disk holds seqs [last_event_id+1 .. min_buffered-1] (the gap).
            for seq, row in backfill_from_disk(run_dir, last_event_id):
                if seq >= min_buffered:
                    break  # the rest is still in the hub buffer; avoid duplicates
                yield format_sse(seq, "game", sse_event_payload(seq, row))
                backfilled_through = seq
        # In-buffer backfill: anything missed before the live queue attached.
        for seq, row in hub.backfill(backfilled_through):
            yield format_sse(seq, "game", sse_event_payload(seq, row))
            backfilled_through = seq
        # Live loop with heartbeat on idle.
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield format_heartbeat()
                continue
            if item is _CLOSED:
                break
            seq, row = item
            if seq <= backfilled_through:
                continue  # already sent during backfill
            yield format_sse(seq, "game", sse_event_payload(seq, row))
    finally:
        hub.unsubscribe(queue)
```

The terminal `system` error event is published onto the hub by `_run_game`'s `finally` (Task 3) before `hub.close()`, so it arrives via the live queue (or backfill on reconnect) exactly like any other event — `_map_event` classifies its `event_type="system"` row as type `"system"` and carries the error in `text`/`message`.

- [ ] Run, verify it PASSES:

```
uv run pytest tests/interface/test_sse_stream.py -v
```

Expected: `test_format_sse_frames_id_event_data PASSED`, `test_sse_event_payload_uses_view_mapping PASSED`, `test_sse_payload_for_five_typed_skills_has_type_skill_and_spec_kind PASSED`, `test_sse_payload_for_sub_phase_has_type_sub_phase PASSED`, `test_backfill_from_disk_returns_seqs_after_cursor PASSED` — 5 passed.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/services/sse_stream.py tests/interface/test_sse_stream.py && git commit -m "feat(api): SSE framing + ViewEvent payload + disk backfill helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6 — Live `stream_game`: backfill→live, eviction→disk gap, terminal error (async)

**Files**
- Modify: `tests/interface/test_sse_stream.py`

This task is the **genuine red-first cycle for the live `stream_game` path**. Task 5 wrote the generator but only its synchronous helpers (`format_sse`/`sse_event_payload`/`backfill_from_disk`) were proven by Task 5's tests; the async live loop, the spec §8 eviction→disk-gap fallback, and the spec §8 terminal `system` error frame are unproven. Write these async tests FIRST and confirm they fail against a `stream_game` that lacks the eviction/error branches before relying on the Task 5 impl. (If you implemented the full Task 5 `stream_game` already, run these to confirm coverage; if you staged Task 5 as a minimal backfill-then-live generator, these are red until the eviction + terminal-error branches land.)

- [ ] Append the async tests (0-based seqs throughout — first event is seq 0):

```python
# tests/interface/test_sse_stream.py  (append)
import json
import pytest

from llm_werewolf.interface.api.services.event_hub import EventHub
from llm_werewolf.interface.api.services.sse_stream import stream_game


class _FakeSession:
    def __init__(self, run_dir=None, error=None) -> None:
        self.hub = EventHub()
        self.run_dir = run_dir
        self.error = error


def _speech_row(pid: int) -> dict:
    return {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
            "message": f"P{pid}", "data": {"player_id": f"player_{pid}",
            "player_name": f"P{pid}", "speech": "x"}}


async def test_stream_game_backfills_then_streams_live() -> None:
    session = _FakeSession()
    session.hub.publish(_speech_row(1))  # seq 0 (before connect)
    session.hub.publish(_speech_row(2))  # seq 1 (before connect)

    frames: list[str] = []
    # Last-Event-ID=0 => client already saw seq 0; backfill seq > 0 (=> seq 1).
    gen = stream_game(session=session, run_dir=__import__("pathlib").Path("."),
                      last_event_id=0)

    frames.append(await gen.__anext__())
    assert "id: 1\n" in frames[0]

    # A live event arrives -> next frame is seq 2.
    session.hub.publish(_speech_row(3))
    frames.append(await gen.__anext__())
    assert "id: 2\n" in frames[1]

    session.hub.close()
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_stream_game_no_duplicate_between_backfill_and_live() -> None:
    session = _FakeSession()
    session.hub.publish(_speech_row(1))  # seq 0, buffered
    # Fresh connection (no Last-Event-ID) => after_seq = -1 => backfill seq >= 0.
    gen = stream_game(session=session, run_dir=__import__("pathlib").Path("."),
                      last_event_id=-1)
    first = await gen.__anext__()  # backfill seq 0
    assert "id: 0\n" in first
    session.hub.close()
    # seq 0 must not be re-emitted as a live item.
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_stream_game_evicted_cursor_backfills_gap_from_disk(tmp_path) -> None:
    # Spec §8: requested Last-Event-ID older than the hub buffer => disk gap fill.
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # Disk holds the full history seq 0..4.
    rows = [_speech_row(i) for i in range(5)]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    session = _FakeSession(run_dir=run_dir)
    session.hub = EventHub(buffer_size=2)  # only the last 2 seqs survive
    for r in rows:
        session.hub.publish(r)  # seqs 0..4; buffer now holds {3, 4}
    assert session.hub.min_buffered_seq == 3

    # Client resumes from Last-Event-ID=0 (seqs 1,2 were EVICTED from the buffer).
    gen = stream_game(session=session, run_dir=run_dir, last_event_id=0)
    seen: list[int] = []
    session.hub.close()  # no further live events; drain backfill then stop
    try:
        while True:
            frame = await gen.__anext__()
            if frame.startswith("id: "):
                seen.append(int(frame.split("\n", 1)[0].removeprefix("id: ")))
    except StopAsyncIteration:
        pass
    # The gap (seq 1,2 from disk) AND the in-buffer seqs (3,4) are all delivered,
    # in order, with NO gap silently skipped.
    assert seen == [1, 2, 3, 4]


async def test_stream_game_terminal_system_error_frame(tmp_path) -> None:
    # Spec §8: _run_game publishes a terminal type=system error event onto the hub
    # before close; it flows through stream_game like any other event.
    session = _FakeSession(run_dir=tmp_path, error="LLM provider timed out")
    # Simulate the Task 3 finally block: publish the system error, then close.
    session.hub.publish({
        "event_type": "system", "round_number": 0, "phase": "ended",
        "message": "LLM provider timed out", "data": {"error": "LLM provider timed out"},
    })
    gen = stream_game(session=session, run_dir=tmp_path, last_event_id=-1)
    session.hub.close()
    frames = []
    try:
        while True:
            frames.append(await gen.__anext__())
    except StopAsyncIteration:
        pass
    body = "".join(frames)
    assert '"type": "system"' in body
    assert "LLM provider timed out" in body
```

- [ ] Run, verify the new tests PASS:

```
uv run pytest tests/interface/test_sse_stream.py -v
```

Expected: 9 passed (5 from Task 5 + 4 new): backfill→live, dedup, eviction→disk-gap fill (`seen == [1, 2, 3, 4]`), and the terminal `system` error frame.

- [ ] Commit:

```
git add tests/interface/test_sse_stream.py && git commit -m "test(api): stream_game live + eviction disk-gap fill + terminal system error

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7 — `GET /games/{run_id}/stream` route (StreamingResponse, no buffering)

**Files**
- Modify: `src/llm_werewolf/interface/api/routes/actions.py`
- Test: `tests/interface/test_api_stream.py`

- [ ] Write the failing integration test (disk backfill path via `Last-Event-ID`; framing + headers):

```python
# tests/interface/test_api_stream.py
"""Integration tests for GET /games/{run_id}/stream (SSE)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from llm_werewolf.interface.api import deps
from llm_werewolf.interface.api.app import create_app


def _write_run(run_dir):
    run_dir.mkdir(parents=True)
    rows = [
        {"event_type": "game_started", "round_number": 0, "phase": "setup",
         "message": "", "data": {}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P1", "data": {"player_id": "player_1", "player_name": "P1", "speech": "a"}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P2", "data": {"player_id": "player_2", "player_name": "P2", "speech": "b"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )


def _client(tmp_path):
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir / "done-1")
    app = create_app()
    app.dependency_overrides[deps.get_runs_dir] = lambda: runs_dir
    app.dependency_overrides[deps.get_eval_runs_dir] = lambda: runs_dir
    return TestClient(app)


def test_stream_finished_run_backfills_from_disk(tmp_path) -> None:
    # 3 disk rows => 0-based seqs 0, 1, 2 (matching build_view's _map_event idx).
    client = _client(tmp_path)
    with client.stream("GET", "/api/v1/games/done-1/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["cache-control"] == "no-cache"
        assert resp.headers["x-accel-buffering"] == "no"
        body = "".join(resp.iter_text())
    assert "id: 0\n" in body
    assert "id: 1\n" in body
    assert "id: 2\n" in body
    assert "event: game\n" in body


def test_stream_last_event_id_skips_seen(tmp_path) -> None:
    # Last-Event-ID=1 => client saw seq 0,1; only seq 2 is backfilled.
    client = _client(tmp_path)
    with client.stream(
        "GET", "/api/v1/games/done-1/stream", headers={"Last-Event-ID": "1"}
    ) as resp:
        body = "".join(resp.iter_text())
    assert "id: 0\n" not in body
    assert "id: 1\n" not in body
    assert "id: 2\n" in body


def test_stream_unknown_run_is_404(tmp_path) -> None:
    client = _client(tmp_path)
    resp = client.get("/api/v1/games/no-such-run/stream")
    assert resp.status_code == 404
```

- [ ] Run, verify it FAILS:

```
uv run pytest tests/interface/test_api_stream.py -v
```

Expected: 404 for `/done-1/stream` (route not registered) → `test_stream_finished_run_backfills_from_disk` and `test_stream_last_event_id_skips_seen` FAIL on assertions; `test_stream_unknown_run_is_404` may incidentally pass.

- [ ] Add imports to `routes/actions.py` (after the existing `fastapi` import, `actions.py:5`):

```python
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
```

- [ ] Add a service import near the existing imports (after `actions.py:24`):

```python
from llm_werewolf.interface.api.services.runs import get_run_detail
from llm_werewolf.interface.api.services.sse_stream import stream_game
```

- [ ] Add the route after `game_view` (after `actions.py:161`):

```python
@router.get("/games/{run_id}/stream")
def game_stream(
    run_id: str,
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> StreamingResponse:
    # 0-based seqs: a fresh connection (no Last-Event-ID) uses after_seq=-1 so
    # the very first event (seq 0) is included; Last-Event-ID=N resumes after N.
    try:
        after_seq = int(last_event_id) if last_event_id else -1
    except ValueError:
        after_seq = -1

    from pathlib import Path

    session = game_session_manager.get_session(run_id)
    if session is not None:
        run_dir = session.run_dir
    else:
        detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        run_dir = Path(detail.path)

    generator = stream_game(session=session, run_dir=run_dir, last_event_id=after_seq)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] Run, verify it PASSES:

```
uv run pytest tests/interface/test_api_stream.py -v
```

Expected: `test_stream_finished_run_backfills_from_disk PASSED`, `test_stream_last_event_id_skips_seen PASSED`, `test_stream_unknown_run_is_404 PASSED` — 3 passed.

- [ ] Commit:

```
git add src/llm_werewolf/interface/api/routes/actions.py tests/interface/test_api_stream.py && git commit -m "feat(api): GET /games/{run_id}/stream SSE with Last-Event-ID resume

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8 — Live SSE end-to-end against a real EventHub session + heartbeat

**Files**
- Modify: `tests/interface/test_api_stream.py`

- [ ] Append the live + heartbeat test (register a fake in-memory session so the route takes the hub path):

```python
# tests/interface/test_api_stream.py  (append)
import threading
import time

from llm_werewolf.interface.api.services.game_sessions import (
    GameSession,
    game_session_manager,
)


def _live_speech_row(pid: int) -> dict:
    return {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
            "message": f"P{pid}", "data": {"player_id": f"player_{pid}",
            "player_name": f"P{pid}", "speech": "x"}}


def test_stream_live_session_pushes_then_closes(tmp_path) -> None:
    game_session_manager.reset()
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "live-1"
    run_dir.mkdir(parents=True)
    session = GameSession(
        run_id="live-1", run_dir=run_dir,
        config_path=run_dir, config_id="c",
    )
    game_session_manager._sessions["live-1"] = session

    app = create_app()
    app.dependency_overrides[deps.get_runs_dir] = lambda: runs_dir
    app.dependency_overrides[deps.get_eval_runs_dir] = lambda: runs_dir
    client = TestClient(app)

    def _producer() -> None:
        time.sleep(0.2)
        session.hub.publish(_live_speech_row(1))  # seq 0
        session.hub.publish(_live_speech_row(2))  # seq 1
        time.sleep(0.1)
        session.hub.close()

    t = threading.Thread(target=_producer)
    t.start()
    with client.stream("GET", "/api/v1/games/live-1/stream") as resp:
        body = "".join(resp.iter_text())
    t.join()
    game_session_manager.reset()

    assert "id: 0\n" in body
    assert "id: 1\n" in body
    assert '"type": "speech"' in body
```

- [ ] Run, verify it PASSES:

```
uv run pytest tests/interface/test_api_stream.py::test_stream_live_session_pushes_then_closes -v
```

Expected: 1 passed (the stream backfills the empty buffer, streams seq 1 and 2 from the live queue, then ends on `close()`).

- [ ] Commit:

```
git add tests/interface/test_api_stream.py && git commit -m "test(api): live SSE session streams hub events then closes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9 — Full milestone verification (suite + lint)

**Files**
- None (verification only)

- [ ] Run the full interface test module set for this milestone:

```
uv run pytest tests/interface/test_event_hub.py tests/interface/test_sse_stream.py tests/interface/test_api_stream.py tests/interface/test_view_service.py tests/interface/test_api_control.py tests/interface/test_api_services.py tests/interface/test_api_actions.py -v
```

Expected: all passed (EventHub 8, sse_stream 9, api_stream 4, the two new test_view_service projection tests, the Task 3b /state surfacing test in test_api_control, plus existing service/action tests green). No regressions in disk format or existing endpoints.

- [ ] Run the broader interface suite to confirm no contract drift in `/view` / `/status`:

```
uv run pytest tests/interface -q
```

Expected: all passed; `events.jsonl`, `/view`, `/status`, replay paths unchanged.

- [ ] Lint the changed Python (repo uses ruff via the test addopts; run ruff explicitly):

```
uv run ruff check src/llm_werewolf/interface/api/services/event_hub.py src/llm_werewolf/interface/api/services/sse_stream.py src/llm_werewolf/interface/api/services/game_sessions.py src/llm_werewolf/interface/api/services/view.py src/llm_werewolf/interface/api/services/state.py src/llm_werewolf/interface/api/models/view.py src/llm_werewolf/interface/api/routes/actions.py
```

Expected: `All checks passed!`

- [ ] Commit any lint fixes (if ruff `--fix` rewrote anything):

```
git add -A && git commit -m "style(api): ruff fixes for EventHub + SSE stream

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```


---

## M5 — Frontend: SSE transport, phase-driven UI, control bar, structured rendering, remove fakes

**Coverage:** Covers spec §7 (Frontend changes) end-to-end and the frontend half of §9 Testing. §7.1 authoritative phase: Task 2 (GamePhase enum + GameStateResponse), Task 3 (isNightPhase), Task 5 (TopHeader off GamePhase), Task 6 (ThreeCanvas off isNightPhase) — deletes the ThreeCanvas `=== 'night'` and TopHeader `.startsWith('night')` string-matches and the fake 30s countdown; game-over collapsed to phase==='ended' in Task 4 (store.isGameOver), Task 9 (App overlay + CardDeck reveal). §7.2 SSE transport: Task 4 replaces the 1000ms poll + 220ms drain with an EventSource on /stream relying on browser auto-reconnect + Last-Event-ID (seq cursor), keeps a small render buffer, maps speed to /control; Task 10 ensures the Vite dev proxy does not buffer text/event-stream (spec §11 risk). §7.3 control bar: Task 7 (ControlPanel pause/resume/single-step/speed→POST /control reflecting play_state). §7.4 structured rendering: Task 4 (eventText for skill/vote/death) + Task 8 (SpeechConsole structured rows + 狼人夜聊中/女巫决策中/预言家查验中 sub-phase highlight). §7.5 suspense toggle preserved: Task 4 shouldMask + Task 9 CardDeck. types.ts rewritten to the §5 state/event/control shapes in Task 2. Verification via npm run lint (tsc --noEmit) and npm run build per spec §9, plus a vitest runner added in Task 1 to make the 'verified against a mock SSE stream' requirement executable. NOT covered (other milestones): all backend/engine work — retain engine, step-pump, control gate, EventHub, SSE endpoint server side, last_night capture, missing phase signals, five typed skill events, widened serialization (M1–M4).

**File structure:**

| File | Action | Responsibility |
|---|---|---|
| `frontend/package.json` | modify | Add vitest + jsdom + @testing-library/react devDeps and a `test` script so the milestone's component/store tests are runnable; keep existing `lint` (tsc --noEmit). |
| `frontend/vitest.config.ts` | create | Vitest config: jsdom environment, globals, setup file; reuses the vite react plugin so .tsx compiles. |
| `frontend/src/test/setup.ts` | create | Test setup: install a minimal EventSource mock on globalThis and import @testing-library/jest-dom matchers. |
| `frontend/src/test/MockEventSource.ts` | create | Controllable EventSource double used by store/SSE tests to emit `message`/`error` events and assert reconnect/Last-Event-ID behavior. |
| `frontend/src/types.ts` | modify | Replace log-mirror types with the engine-driven contract: GamePhase/SubPhase/PlayState enums, GameStateResponse (status/play_state/speed/phase/sub_phase/round/current_actor_seat/winner/last_night/votes/cursor/players), StreamEvent (seq/type/sub_phase/round + skill/vote/death structures + new types), ControlRequest/ControlResponse, phase/sub-phase Chinese label maps. |
| `frontend/src/lib/api.ts` | create | Typed API helpers: fetchState(runId), postControl(runId, req), streamUrl(runId), plus isNightPhase(phase) and PHASE_LABELS/SUB_PHASE_LABELS so no component string-matches again. |
| `frontend/src/lib/api.test.ts` | create | Unit tests for fetchState/postControl URL+payload shape and isNightPhase / label maps. |
| `frontend/src/store.ts` | modify | Replace 1000ms poll + 220ms drain with an EventSource subscription to /stream (auto-reconnect + Last-Event-ID via seq) and a GET /state authoritative refresh; rename day->round; add gameState (GameStateResponse) + playState + controlGame()/stepGame() calling POST /control; keep client suspense masking and render buffer. |
| `frontend/src/store.test.ts` | create | Tests: SSE message appends a RenderLog; /state refresh updates phase/round/play_state/winner; controlGame('pause') POSTs the right body and reflects play_state; game-over is phase==='ended' only. |
| `frontend/src/components/TopHeader.tsx` | modify | Delete the fake 30s countdown and `.startsWith('night')`; drive night/day + labels off GamePhase via isNightPhase/PHASE_LABELS; show round + sub-phase highlight; read gameState. |
| `frontend/src/components/ThreeCanvas.tsx` | modify | Replace `phase === 'night'` string match with isNightPhase(gameState.phase); read phase/players from the new gameState/store fields. |
| `frontend/src/components/ControlPanel.tsx` | modify | Wire Pause/Resume/Single-step/Speed to POST /control via store.controlGame/stepGame; reflect play_state (not local isPlaying); speed 1|2|4 from engine. |
| `frontend/src/components/SpeechConsole.tsx` | modify | Render structured ev.skill/ev.vote/ev.death rows (kind + actor/target/cause) and show the current sub-phase highlight banner (狼人夜聊中/女巫决策中/预言家查验中). |
| `frontend/src/components/CardDeck.tsx` | modify | Read winner/players from gameState; expose roles on phase==='ended' (replacing snapshot.winner) so suspense reveal stays correct. |
| `frontend/src/App.tsx` | modify | Game-over overlay keyed solely on gameState.phase==='ended' (remove dual snapshot.winner signal); pass winner from gameState; update inSetup check to new status values. |

> Depends on M1–M4 being merged: `GET /api/v1/games/{run_id}/state`, `GET /api/v1/games/{run_id}/stream` (SSE), and `POST /api/v1/games/{run_id}/control` exist and return the shapes in §5 of the spec. This milestone only touches `frontend/`.
>
> **Test tooling note.** The frontend currently has **no test runner** — `npm run lint` is `tsc --noEmit` and vitest is not installed. The spec's frontend verification is *"`npm run lint` clean; phase-driven rendering and control wiring verified against a mock SSE stream."* Task 1 installs a real runner so the TDD steps below are executable; every task ends with both `npx vitest run <file>` (behavior) and `npm run lint` (types). All commands assume `cwd = frontend/`.

---

### Task 1 — Install a frontend test runner + mock EventSource

**Files**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/MockEventSource.ts`
- Test (sanity): `frontend/src/test/setup.smoke.test.ts`

- [ ] Add dev dependencies and a `test` script. Run:
```bash
cd frontend && npm install -D vitest@^2 jsdom@^25 @testing-library/react@^16 @testing-library/jest-dom@^6
```
Expected: install succeeds; `package.json` `devDependencies` now lists `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`.

- [ ] Add the `test` script to `frontend/package.json` (keep `lint` unchanged):
```json
    "lint": "tsc --noEmit",
    "test": "vitest run"
```

- [ ] Create `frontend/vitest.config.ts`:
```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
```

- [ ] Create `frontend/src/test/MockEventSource.ts` — a controllable EventSource double:
```ts
type Listener = (ev: MessageEvent) => void;

export class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  lastEventId = "";
  withCredentials = false;
  readyState = 0; // CONNECTING
  onmessage: Listener | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onopen: ((ev: Event) => void) | null = null;
  private listeners: Record<string, Listener[]> = {};
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, fn: Listener) {
    (this.listeners[type] ||= []).push(fn);
  }
  removeEventListener(type: string, fn: Listener) {
    this.listeners[type] = (this.listeners[type] || []).filter((l) => l !== fn);
  }
  close() {
    this.closed = true;
    this.readyState = 2; // CLOSED
  }

  // ---- test helpers ----
  emit(data: unknown, opts: { id?: string } = {}) {
    if (opts.id) this.lastEventId = opts.id;
    const ev = new MessageEvent("message", {
      data: typeof data === "string" ? data : JSON.stringify(data),
      lastEventId: opts.id ?? this.lastEventId,
    });
    this.onmessage?.(ev);
    (this.listeners["message"] || []).forEach((l) => l(ev));
  }
  emitError() {
    const ev = new Event("error");
    this.onerror?.(ev);
    (this.listeners["error"] || []).forEach((l) => l(ev as MessageEvent));
  }

  static reset() {
    MockEventSource.instances = [];
  }
  static latest(): MockEventSource {
    return MockEventSource.instances[MockEventSource.instances.length - 1];
  }
}
```

- [ ] Create `frontend/src/test/setup.ts` — install the mock globally and load jest-dom matchers:
```ts
import "@testing-library/jest-dom/vitest";
import { beforeEach, vi } from "vitest";
import { MockEventSource } from "./MockEventSource";

// EventSource does not exist in jsdom; install the controllable double.
vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

beforeEach(() => {
  MockEventSource.reset();
  vi.restoreAllMocks();
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);
});
```

- [ ] Write the smoke test `frontend/src/test/setup.smoke.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { MockEventSource } from "./MockEventSource";

describe("test harness", () => {
  it("exposes EventSource as the mock", () => {
    const es = new EventSource("/x");
    expect(es).toBeInstanceOf(MockEventSource);
    expect(MockEventSource.latest().url).toBe("/x");
  });
});
```

- [ ] Run it, verify it PASSES:
```bash
cd frontend && npx vitest run src/test/setup.smoke.test.ts
```
Expected: `Test Files  1 passed (1)` / `Tests  1 passed (1)`.

- [ ] Lint stays clean:
```bash
cd frontend && npm run lint
```
Expected: no output, exit code 0.

- [ ] Commit:
```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/test/ && git commit -m "test(frontend): add vitest+jsdom runner and MockEventSource harness"
```

---

### Task 2 — Rewrite `types.ts` to the engine-driven contract

**Files**
- Modify: `frontend/src/types.ts`
- Test: `frontend/src/types.test.ts`

- [ ] Write the failing test `frontend/src/types.test.ts` (type-shape assertions compile-checked + runtime label-map checks):
```ts
import { describe, expect, it } from "vitest";
import {
  GamePhase,
  PlayState,
  PHASE_LABELS,
  SUB_PHASE_LABELS,
  type GameStateResponse,
  type StreamEvent,
} from "./types";

describe("engine-driven contract types", () => {
  it("GamePhase has the 6 authoritative members", () => {
    expect(Object.values(GamePhase)).toEqual([
      "setup", "night", "sheriff_election", "day_discussion", "day_voting", "ended",
    ]);
  });

  it("PlayState matches /control play_state", () => {
    expect(Object.values(PlayState)).toEqual(["playing", "paused"]);
  });

  it("every phase and key sub-phase has a Chinese label", () => {
    expect(PHASE_LABELS[GamePhase.night]).toBe("黑夜");
    expect(PHASE_LABELS[GamePhase.day_discussion]).toBe("白天讨论");
    expect(SUB_PHASE_LABELS.werewolf_chat).toBe("狼人夜聊中");
    expect(SUB_PHASE_LABELS.witch_decide).toBe("女巫决策中");
    expect(SUB_PHASE_LABELS.seer_check).toBe("预言家查验中");
  });

  it("GameStateResponse / StreamEvent expose the spec fields", () => {
    const state: GameStateResponse = {
      status: "running", error: null, play_state: "playing", speed: 1,
      phase: GamePhase.night, sub_phase: "werewolf_chat", round: 2,
      current_actor_seat: 5, winner: null, sheriff_seat: 3,
      alive_count: 6, dead_count: 2,
      last_night: { deaths: [{ seat: 7, cause: "wolf_kill" }], saved_seat: null, guarded_seat: 4, poisoned_seat: null },
      votes: { by_seat: { "1": 5 }, tally: { "5": 1 } },
      cursor: 142,
      players: [{ seat: 1, name: "A", role: "Seer", camp: "villager", is_alive: true, is_sheriff: false, model: "deepseek-chat", status_flags: ["alive"] }],
    };
    const ev: StreamEvent = {
      seq: 143, type: "skill", phase: GamePhase.night, sub_phase: "werewolf_chat", round: 2,
      reveal: "now", visibility: "wolf",
      skill: { kind: "wolf_kill", actor: { seat: 1 }, target: { seat: 7 }, result: null },
    };
    expect(state.last_night?.deaths[0].seat).toBe(7);
    expect(ev.skill?.kind).toBe("wolf_kill");
  });
});
```

- [ ] Run it, verify it FAILS:
```bash
cd frontend && npx vitest run src/types.test.ts
```
Expected: fails to import — e.g. `SyntaxError: The requested module './types' does not provide an export named 'GamePhase'`.

- [ ] Replace the whole contents of `frontend/src/types.ts` with the engine-driven contract:
```ts
// ===== Engine-driven game API contract (mirrors docs/.../engine-driven-game-api-design §5) =====

export enum GamePhase {
  setup = "setup",
  night = "night",
  sheriff_election = "sheriff_election",
  day_discussion = "day_discussion",
  day_voting = "day_voting",
  ended = "ended",
}

export enum PlayState {
  playing = "playing",
  paused = "paused",
}

export type SessionStatus = "running" | "paused" | "ended" | "cancelled" | "error";
export type SubPhase =
  | "werewolf_chat" | "witch_decide" | "seer_check" | "guard_decide"
  | "hunter_decide" | "graveyard_check" | string;

export type RevealMode = "now" | "on_death" | "on_game_end";
export type Visibility = "public" | "wolf" | "god";

export type StreamEventType =
  | "speech" | "skill" | "vote" | "death" | "phase" | "sub_phase"
  | "belief" | "vote_intention" | "system";

export type SkillKind =
  | "wolf_kill" | "white_wolf_kill" | "wolf_beauty_charm" | "nightmare_block"
  | "guardian_wolf_guard" | "raven_mark" | "witch_save" | "witch_poison"
  | "seer_check" | "guard" | "graveyard_check" | "hunter_shoot" | "badge_transfer"
  | string;

export const PHASE_LABELS: Record<GamePhase, string> = {
  [GamePhase.setup]: "准备",
  [GamePhase.night]: "黑夜",
  [GamePhase.sheriff_election]: "警长竞选",
  [GamePhase.day_discussion]: "白天讨论",
  [GamePhase.day_voting]: "白天投票",
  [GamePhase.ended]: "对局结束",
};

export const SUB_PHASE_LABELS: Record<string, string> = {
  werewolf_chat: "狼人夜聊中",
  witch_decide: "女巫决策中",
  seer_check: "预言家查验中",
  guard_decide: "守卫守护中",
  hunter_decide: "猎人决策中",
  graveyard_check: "盗墓查验中",
};

export interface StatePlayer {
  seat: number;
  name: string;
  role: string | null;
  camp: string | null;
  is_alive: boolean;
  is_sheriff: boolean;
  model: string | null;
  status_flags: string[];
}

export interface LastNight {
  deaths: { seat: number; cause: string }[];
  saved_seat: number | null;
  guarded_seat: number | null;
  poisoned_seat: number | null;
}

export interface VotesState {
  by_seat: Record<string, number>;
  tally: Record<string, number>;
}

export interface GameStateResponse {
  status: SessionStatus;
  error: string | null;
  play_state: PlayState | "playing" | "paused";
  speed: 1 | 2 | 4;
  phase: GamePhase;
  sub_phase: SubPhase | null;
  round: number;
  current_actor_seat: number | null;
  winner: string | null;
  sheriff_seat: number | null;
  alive_count: number;
  dead_count: number;
  last_night: LastNight | null;
  votes: VotesState | null;
  cursor: number;
  players: StatePlayer[];
}

export interface StreamEvent {
  seq: number;
  type: StreamEventType;
  phase: GamePhase;
  sub_phase: SubPhase | null;
  round: number;
  reveal: RevealMode;
  visibility: Visibility;
  // speech
  speaker?: { seat: number | null; name?: string | null } | null;
  public_text?: string | null;
  private_thought?: string | null;
  // skill
  skill?: { kind: SkillKind; actor?: { seat: number | null }; target?: { seat: number | null }; result?: unknown } | null;
  // vote
  vote?: { voter?: { seat: number | null }; target?: { seat: number | null } } | null;
  // death
  death?: { seat: number | null; name?: string | null; cause?: string | null } | null;
  // phase / sub_phase / system display hint
  name?: string | null;
  text?: string | null;
}

export interface ControlRequest {
  action: "pause" | "resume" | "step" | "speed";
  value?: 1 | 2 | 4;
}

export interface ControlResponse {
  run_id: string;
  play_state: PlayState | "playing" | "paused";
  speed: 1 | 2 | 4;
  phase: GamePhase;
}

// ===== Per-seat LLM 配置（开局用，沿用 wolfcha ModelRef）=====

export interface SeatConfig {
  seat: number;
  name: string;
  provider: string;     // 仅前端分组；后端以 base_url 为准
  model: string;
  base_url: string;
  temperature?: number;
}

export interface ProviderPreset {
  id: string;
  label: string;
  base_url: string;
  models: string[];
}

// ===== 前端本地展示用的渲染日志条目 =====

export interface RenderLog {
  seq: number;
  kind: StreamEventType;
  round: number;
  speakerSeat: number | null;
  speakerName: string;
  text: string;            // 已揭示/遮挡处理后的展示文本
  privateThought?: string | null;
  visibility: Visibility;
}
```

- [ ] Run the test, verify it PASSES:
```bash
cd frontend && npx vitest run src/types.test.ts
```
Expected: `Tests  4 passed (4)`.

- [ ] Lint will surface every downstream component still using the old fields (`day`, `phase_label`, `ViewSnapshot`, `ViewResponse`) — that is expected and will be fixed in Tasks 4–9. For now, confirm `types.ts` itself compiles in isolation:
```bash
cd frontend && npx tsc --noEmit src/types.ts
```
Expected: no output, exit code 0.

- [ ] Commit:
```bash
git add frontend/src/types.ts frontend/src/types.test.ts && git commit -m "feat(frontend): replace log-mirror types with engine-driven contract (GamePhase/StreamEvent/Control)"
```

---

### Task 3 — Typed API helpers (`lib/api.ts`)

**Files**
- Create: `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api.test.ts`

- [ ] Write the failing test `frontend/src/lib/api.test.ts`:
```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchState, postControl, streamUrl, isNightPhase } from "./api";
import { GamePhase } from "../types";

afterEach(() => vi.restoreAllMocks());

describe("api helpers", () => {
  it("streamUrl points at the SSE endpoint", () => {
    expect(streamUrl("r1")).toBe("/api/v1/games/r1/stream");
  });

  it("isNightPhase is true only for night/setup", () => {
    expect(isNightPhase(GamePhase.night)).toBe(true);
    expect(isNightPhase(GamePhase.setup)).toBe(true);
    expect(isNightPhase(GamePhase.day_discussion)).toBe(false);
    expect(isNightPhase(GamePhase.day_voting)).toBe(false);
    expect(isNightPhase(GamePhase.ended)).toBe(false);
  });

  it("fetchState GETs /state and unwraps the body", async () => {
    const body = { phase: "night", round: 1 };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => body });
    vi.stubGlobal("fetch", fetchMock);
    const state = await fetchState("r1");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/games/r1/state");
    expect(state.phase).toBe("night");
  });

  it("postControl POSTs the action body and returns the response", async () => {
    const resp = { run_id: "r1", play_state: "paused", speed: 2, phase: "night" };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => resp });
    vi.stubGlobal("fetch", fetchMock);
    const out = await postControl("r1", { action: "speed", value: 2 });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/games/r1/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "speed", value: 2 }),
    });
    expect(out.play_state).toBe("paused");
  });
});
```

- [ ] Run it, verify it FAILS:
```bash
cd frontend && npx vitest run src/lib/api.test.ts
```
Expected: `Failed to resolve import "./api"` / module not found.

- [ ] Create `frontend/src/lib/api.ts`:
```ts
import { ControlRequest, ControlResponse, GamePhase, GameStateResponse } from "../types";

export const API = "/api/v1";

function unwrap<T>(json: unknown): T {
  return (json && typeof json === "object" && "data" in (json as Record<string, unknown>)
    ? (json as { data: T }).data
    : json) as T;
}

export function streamUrl(runId: string): string {
  return `${API}/games/${runId}/stream`;
}

export async function fetchState(runId: string): Promise<GameStateResponse> {
  const res = await fetch(`${API}/games/${runId}/state`);
  if (!res.ok) throw new Error(`state failed: HTTP ${res.status}`);
  return unwrap<GameStateResponse>(await res.json());
}

export async function postControl(runId: string, req: ControlRequest): Promise<ControlResponse> {
  const res = await fetch(`${API}/games/${runId}/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`control failed: HTTP ${res.status}`);
  return unwrap<ControlResponse>(await res.json());
}

// Single authoritative night/day predicate — replaces every component string-match.
export function isNightPhase(phase: GamePhase | null | undefined): boolean {
  return phase === GamePhase.night || phase === GamePhase.setup;
}
```

- [ ] Run the test, verify it PASSES:
```bash
cd frontend && npx vitest run src/lib/api.test.ts
```
Expected: `Tests  4 passed (4)`.

- [ ] Commit:
```bash
git add frontend/src/lib/api.ts frontend/src/lib/api.test.ts && git commit -m "feat(frontend): typed /state + /control api helpers and isNightPhase predicate"
```

---

### Task 4 — Rewrite the store: SSE transport, `/state` refresh, control actions

**Files**
- Modify: `frontend/src/store.ts`
- Test: `frontend/src/store.test.ts`

- [ ] Write the failing test `frontend/src/store.test.ts`:
```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useGameStore } from "./store";
import { MockEventSource } from "./test/MockEventSource";
import { GamePhase } from "./types";

function resetStore() {
  useGameStore.getState().exitToSetup();
  useGameStore.setState({ runId: "r1" });
}

beforeEach(() => {
  resetStore();
  MockEventSource.reset();
});

describe("store SSE transport", () => {
  it("appends a RenderLog when a speech event arrives on the stream", () => {
    useGameStore.getState()._openStream("r1");
    const es = MockEventSource.latest();
    es.emit(
      {
        seq: 1, type: "speech", phase: "day_discussion", sub_phase: null, round: 2,
        reveal: "now", visibility: "public",
        speaker: { seat: 3, name: "C" }, public_text: "hello", private_thought: "psst",
      },
      { id: "1" },
    );
    const logs = useGameStore.getState().logs;
    expect(logs).toHaveLength(1);
    expect(logs[0].kind).toBe("speech");
    expect(logs[0].speakerSeat).toBe(3);
    expect(logs[0].text).toBe("hello");
    expect(useGameStore.getState().cursor).toBe(1);
  });

  it("game-over is driven solely by gameState.phase === 'ended'", async () => {
    const state = {
      status: "ended", error: null, play_state: "paused", speed: 1,
      phase: "ended", sub_phase: null, round: 4, current_actor_seat: null,
      winner: "good", sheriff_seat: null, alive_count: 3, dead_count: 3,
      last_night: null, votes: null, cursor: 99, players: [],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => state }));
    await useGameStore.getState()._refreshState();
    expect(useGameStore.getState().gameState?.phase).toBe(GamePhase.ended);
    expect(useGameStore.getState().isGameOver()).toBe(true);
  });

  it("controlGame('pause') POSTs the action and reflects play_state", async () => {
    const resp = { run_id: "r1", play_state: "paused", speed: 1, phase: "night" };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => resp });
    vi.stubGlobal("fetch", fetchMock);
    await useGameStore.getState().controlGame("pause");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/games/r1/control",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ action: "pause" }) }),
    );
    expect(useGameStore.getState().playState).toBe("paused");
  });
});
```

- [ ] Run it, verify it FAILS:
```bash
cd frontend && npx vitest run src/store.test.ts
```
Expected: fails — `_openStream`/`_refreshState`/`controlGame`/`isGameOver`/`gameState`/`playState` are not on the store yet (`TypeError: ..._openStream is not a function`).

- [ ] Replace the whole contents of `frontend/src/store.ts`:
```ts
import { create } from "zustand";
import {
  ControlRequest, GamePhase, GameStateResponse, PlayState, RenderLog,
  SeatConfig, StreamEvent, Visibility,
} from "./types";
import { API, fetchState, postControl, streamUrl } from "./lib/api";
import { getApiKey, providerById } from "./lib/api-keys";

type Speed = 1 | 2 | 4;
type RevealView = "god" | "suspense";

interface GameStore {
  runId: string | null;
  status: GameStateResponse["status"] | "idle";
  gameState: GameStateResponse | null;
  logs: RenderLog[];
  cursor: number;
  queue: StreamEvent[];
  playState: PlayState | "playing" | "paused";
  speed: Speed;
  revealView: RevealView;
  error: string | null;

  startGame: (seats: SeatConfig[], opts?: { language?: string; enableSheriff?: boolean }) => Promise<void>;
  cancelGame: () => Promise<void>;
  controlGame: (action: "pause" | "resume" | "step") => Promise<void>;
  stepGame: () => Promise<void>;
  setSpeed: (s: Speed) => Promise<void>;
  setRevealView: (v: RevealView) => void;
  isGameOver: () => boolean;
  exitToSetup: () => void;
  _openStream: (runId: string) => void;
  _refreshState: () => Promise<void>;
  _drain: () => void;
}

let eventSource: EventSource | null = null;
let stateTimer: ReturnType<typeof setInterval> | null = null;
let drainTimer: ReturnType<typeof setInterval> | null = null;

const STATE_REFRESH_MS = 1500; // authoritative phase/round/play_state poll (cheap, no events)
const DRAIN_MS = 220;

function teardown() {
  if (eventSource) { eventSource.close(); eventSource = null; }
  if (stateTimer) { clearInterval(stateTimer); stateTimer = null; }
  if (drainTimer) { clearInterval(drainTimer); drainTimer = null; }
}

function shouldMask(ev: StreamEvent, view: RevealView): boolean {
  if (view === "god") return false;
  return ev.reveal !== "now"; // suspense: on_death / on_game_end 暂时遮挡
}

function eventText(ev: StreamEvent): string {
  if (ev.type === "speech") return ev.public_text || ev.text || "";
  if (ev.type === "skill" && ev.skill) {
    const a = ev.skill.actor?.seat ?? "?";
    const t = ev.skill.target?.seat;
    return t != null ? `技能：${ev.skill.kind}（${a}号 → ${t}号）` : `技能：${ev.skill.kind}（${a}号）`;
  }
  if (ev.type === "vote" && ev.vote) {
    return `投票：${ev.vote.voter?.seat ?? "?"}号 → ${ev.vote.target?.seat ?? "?"}号`;
  }
  if (ev.type === "death" && ev.death) {
    return `出局：${ev.death.seat ?? "?"}号（${ev.death.cause ?? "未知"}）`;
  }
  return ev.text || ev.name || "";
}

function toRenderLog(ev: StreamEvent, view: RevealView): RenderLog {
  const masked = shouldMask(ev, view);
  let text = eventText(ev);
  if (masked) {
    text = ev.type === "speech" ? "🌙 有角色在暗中交流…" : "🌙 夜间有角色行动了…";
  }
  return {
    seq: ev.seq,
    kind: ev.type,
    round: ev.round,
    speakerSeat: ev.speaker?.seat ?? ev.skill?.actor?.seat ?? null,
    speakerName: ev.speaker?.name ?? "",
    text,
    privateThought: view === "god" ? ev.private_thought ?? null : null,
    visibility: ev.visibility as Visibility,
  };
}

export const useGameStore = create<GameStore>((set, get) => ({
  runId: null,
  status: "idle",
  gameState: null,
  logs: [],
  cursor: 0,
  queue: [],
  playState: "playing",
  speed: 1,
  revealView: "god",
  error: null,

  startGame: async (seats, opts) => {
    teardown();
    set({ status: "running", logs: [], cursor: 0, queue: [], gameState: null, error: null, playState: "playing" });
    const players = seats.map((s) => ({
      name: s.name,
      model: s.model,
      base_url: s.base_url || providerById(s.provider)?.base_url,
      api_key: getApiKey(s.provider),
      temperature: s.temperature,
    }));
    try {
      const res = await fetch(`${API}/games/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          participation: "all_agent",
          rules: opts?.enableSheriff ? "badge_flow" : "basic",
          player_count: seats.length,
          badge_flow: !!opts?.enableSheriff,
          players,
        }),
      });
      if (!res.ok) { set({ status: "error", error: `start failed: HTTP ${res.status}` }); return; }
      const body = await res.json();
      const data = (body && "data" in body ? body.data : body) as { run_id?: string };
      if (!data?.run_id) { set({ status: "error", error: "start failed: no run_id" }); return; }
      set({ runId: data.run_id });
      get()._openStream(data.run_id);
      stateTimer = setInterval(() => get()._refreshState(), STATE_REFRESH_MS);
      drainTimer = setInterval(() => get()._drain(), DRAIN_MS);
      get()._refreshState();
    } catch (err) {
      console.error("startGame failed", err);
      set({ status: "error", error: String(err) });
    }
  },

  // SSE subscription — relies on the browser's built-in auto-reconnect + Last-Event-ID.
  _openStream: (runId) => {
    if (eventSource) eventSource.close();
    const es = new EventSource(streamUrl(runId));
    es.onmessage = (msg: MessageEvent) => {
      try {
        const ev = JSON.parse(msg.data) as StreamEvent;
        set((st) => ({
          queue: [...st.queue, ev],
          cursor: Math.max(st.cursor, ev.seq),
        }));
      } catch (err) {
        console.error("bad SSE payload", err);
      }
    };
    es.onerror = () => { /* browser auto-reconnects with Last-Event-ID; nothing to do */ };
    eventSource = es;
  },

  // Authoritative phase/round/play_state/winner + full-snapshot fallback.
  _refreshState: async () => {
    const { runId } = get();
    if (!runId) return;
    try {
      const state = await fetchState(runId);
      set({ gameState: state, status: state.status, playState: state.play_state, speed: state.speed, error: state.error });
      if (state.phase === GamePhase.ended || state.status === "cancelled" || state.status === "error") {
        if (stateTimer) { clearInterval(stateTimer); stateTimer = null; }
        if (eventSource) { eventSource.close(); eventSource = null; }
      }
    } catch (err) {
      console.error("state refresh failed", err);
    }
  },

  _drain: () => {
    const { playState, queue, speed, revealView } = get();
    if (playState !== "playing" || queue.length === 0) return;
    const take = Math.max(speed, 1);
    const batch = queue.slice(0, take);
    const rest = queue.slice(take);
    set((st) => ({
      queue: rest,
      logs: [...st.logs, ...batch.map((ev) => toRenderLog(ev, revealView))],
    }));
  },

  cancelGame: async () => {
    const { runId } = get();
    if (runId) {
      try { await fetch(`${API}/games/${runId}/cancel`, { method: "POST" }); } catch { /* ignore */ }
    }
    teardown();
    set({ status: "cancelled" });
  },

  controlGame: async (action) => {
    const { runId } = get();
    if (!runId) return;
    try {
      const resp = await postControl(runId, { action } as ControlRequest);
      set({ playState: resp.play_state, speed: resp.speed as Speed });
    } catch (err) {
      console.error("control failed", err);
    }
  },

  stepGame: async () => {
    const { runId } = get();
    if (!runId) return;
    try {
      const resp = await postControl(runId, { action: "step" });
      set({ playState: resp.play_state });
    } catch (err) {
      console.error("step failed", err);
    }
  },

  setSpeed: async (s) => {
    const { runId } = get();
    set({ speed: s });
    if (!runId) return;
    try {
      const resp = await postControl(runId, { action: "speed", value: s });
      set({ speed: resp.speed as Speed, playState: resp.play_state });
    } catch (err) {
      console.error("speed failed", err);
    }
  },

  setRevealView: (v) => set({ revealView: v }),

  isGameOver: () => get().gameState?.phase === GamePhase.ended,

  exitToSetup: () => {
    teardown();
    set({ runId: null, status: "idle", gameState: null, logs: [], cursor: 0, queue: [], error: null, playState: "playing" });
  },
}));
```

- [ ] Run the test, verify it PASSES:
```bash
cd frontend && npx vitest run src/store.test.ts
```
Expected: `Tests  3 passed (3)`.

- [ ] Commit:
```bash
git add frontend/src/store.ts frontend/src/store.test.ts && git commit -m "feat(frontend): EventSource /stream transport + /state refresh + /control actions in store"
```

---

### Task 5 — `TopHeader`: drive off GamePhase, delete the fake countdown

**Files**
- Modify: `frontend/src/components/TopHeader.tsx`
- Test: `frontend/src/components/TopHeader.test.tsx`

- [ ] Write the failing test `frontend/src/components/TopHeader.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import TopHeader from "./TopHeader";
import { useGameStore } from "../store";
import { GamePhase, GameStateResponse } from "../types";

function setState(partial: Partial<GameStateResponse>) {
  const base: GameStateResponse = {
    status: "running", error: null, play_state: "playing", speed: 1,
    phase: GamePhase.day_discussion, sub_phase: null, round: 1, current_actor_seat: null,
    winner: null, sheriff_seat: null, alive_count: 6, dead_count: 0,
    last_night: null, votes: null, cursor: 0, players: [],
  };
  useGameStore.setState({ gameState: { ...base, ...partial }, status: "running" });
}

afterEach(() => useGameStore.getState().exitToSetup());

describe("TopHeader", () => {
  it("shows the night title when phase is night (no .startsWith match)", () => {
    setState({ phase: GamePhase.night, round: 2 });
    render(<TopHeader />);
    expect(screen.getByText(/第 2 晚/)).toBeInTheDocument();
  });

  it("shows the day-discussion phase label and round", () => {
    setState({ phase: GamePhase.day_discussion, round: 3 });
    render(<TopHeader />);
    expect(screen.getByText(/第 3 日/)).toBeInTheDocument();
    expect(screen.getByText("白天讨论")).toBeInTheDocument();
  });

  it("renders the sub-phase highlight when present and renders no fake countdown", () => {
    setState({ phase: GamePhase.night, sub_phase: "werewolf_chat", round: 1 });
    render(<TopHeader />);
    expect(screen.getByText("狼人夜聊中")).toBeInTheDocument();
    // The fake "00:30" countdown must be gone.
    expect(screen.queryByText(/00:\d\d/)).not.toBeInTheDocument();
  });
});
```

- [ ] Run it, verify it FAILS:
```bash
cd frontend && npx vitest run src/components/TopHeader.test.tsx
```
Expected: fails — the fake `00:30` countdown still renders (so `queryByText(/00:\d\d/)` matches) and `gameState` is unused, so the day/round text comes from the old `snapshot` path.

- [ ] Replace the whole contents of `frontend/src/components/TopHeader.tsx`:
```tsx
import React, { useEffect, useState } from "react";
import { Sun, Moon, Flame, LogOut, Activity } from "lucide-react";
import { useGameStore } from "../store";
import { GamePhase, PHASE_LABELS, SUB_PHASE_LABELS } from "../types";
import { isNightPhase } from "../lib/api";

export default function TopHeader() {
  const gameState = useGameStore((s) => s.gameState);
  const exitToSetup = useGameStore((s) => s.exitToSetup);

  const phase = gameState?.phase ?? GamePhase.setup;
  const round = gameState?.round ?? 0;
  const alive = gameState?.alive_count ?? 0;
  const dead = gameState?.dead_count ?? 0;
  const phaseLabel = PHASE_LABELS[phase] ?? "";
  const subPhaseLabel = gameState?.sub_phase ? SUB_PHASE_LABELS[gameState.sub_phase] ?? gameState.sub_phase : null;
  const ended = phase === GamePhase.ended;
  const isNight = isNightPhase(phase);

  const [confirmExit, setConfirmExit] = useState(false);
  useEffect(() => {
    if (confirmExit) {
      const timer = setTimeout(() => setConfirmExit(false), 4000);
      return () => clearTimeout(timer);
    }
  }, [confirmExit]);

  return (
    <div className="w-full bg-black/45 backdrop-blur-md border-b border-zinc-900/60 px-6 py-1.5 shrink-0 flex items-center justify-between relative z-10 shadow-md">

      {/* Dynamic logo / indicator */}
      <div className="flex items-center gap-1">
        <div className="w-1.5 h-5 bg-red-650" />
        <div className="w-0.5 h-5 bg-red-800" />
        <div className="hidden sm:flex flex-col ml-2 font-sans text-[9px] text-zinc-100 uppercase tracking-widest font-black leading-tight">
          <span>狼人杀神圣审判厅</span>
          <span className="text-[8px] text-zinc-500">{ended ? "已结案" : "对决轮转中"}</span>
        </div>
      </div>

      {/* Centerpiece: phase badge driven by GamePhase */}
      <div className="flex items-center gap-4 bg-black/55 backdrop-blur-xs border border-zinc-800/50 px-6 py-1 rounded relative shadow-[0_2px_4px_rgba(0,0,0,0.4)]"
           style={{ clipPath: "polygon(0 0, 100% 0, 95% 100%, 5% 100%)" }}>

        <div className="flex items-center gap-2">
          {isNight ? (
            <div className="w-7 h-7 rounded-full bg-black border-2 border-[#ef4444] flex items-center justify-center text-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]">
              <Moon className="w-4 h-4 fill-red-500 animate-pulse" />
            </div>
          ) : (
            <div className="w-7 h-7 rounded-full bg-black border-2 border-yellow-500 flex items-center justify-center text-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]">
              <Sun className="w-4 h-4 animate-spin-slow" />
            </div>
          )}

          <div className="flex flex-col">
            <span className="font-serif font-black text-xs text-zinc-100 tracking-wider">
              {isNight ? `夜暮降临 • 第 ${round} 晚` : `曙光黎明 • 第 ${round} 日`}
            </span>
            <span className="font-mono text-[9px] text-[#eab308]/90 tracking-widest font-black uppercase">
              {phaseLabel}
            </span>
          </div>
        </div>

        {/* Sub-phase highlight (display hint, not a pause point) */}
        {subPhaseLabel && (
          <>
            <div className="w-1 h-6 bg-zinc-800" />
            <div className="flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-fuchsia-400 animate-pulse" />
              <span className="font-mono font-black text-[11px] tracking-wider text-fuchsia-300">
                {subPhaseLabel}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Right-side stats + exit */}
      <div className="flex items-center gap-4">
        <div className="text-right font-mono text-[9.5px] leading-tight hidden xs:block">
          <div className="text-yellow-500 font-extrabold uppercase tracking-wider">存活: {alive}名</div>
          <div className="text-red-600 font-black uppercase tracking-wider mt-0.5">出局: {dead}名</div>
        </div>

        <button
          onClick={() => {
            if (confirmExit) { exitToSetup(); setConfirmExit(false); }
            else setConfirmExit(true);
          }}
          className={`h-7 px-2.5 rounded border text-[10px] font-sans font-bold tracking-wider cursor-pointer flex items-center gap-1 transition-all duration-200 ${
            confirmExit
              ? "border-red-500 bg-red-600 text-white shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse"
              : "border-red-900/60 bg-red-950/30 hover:bg-red-900/40 text-red-100 hover:text-white"
          }`}
          title="退出当前游戏"
          id="exit-game-header-btn"
        >
          <LogOut className="w-3 h-3" style={{ animationDuration: confirmExit ? "1.5s" : "0s" }} />
          <span>{confirmExit ? "二次点击确认退出" : "退出游戏"}</span>
        </button>

        <div className="w-7 h-7 rounded border border-zinc-800/40 bg-black/40 flex items-center justify-center shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
          <Flame className="w-3.5 h-3.5 text-red-500 animate-pulse" />
        </div>
      </div>
    </div>
  );
}
```

- [ ] Run the test, verify it PASSES:
```bash
cd frontend && npx vitest run src/components/TopHeader.test.tsx
```
Expected: `Tests  3 passed (3)`.

- [ ] Commit:
```bash
git add frontend/src/components/TopHeader.tsx frontend/src/components/TopHeader.test.tsx && git commit -m "feat(frontend): TopHeader drives off GamePhase + sub-phase highlight, drop fake 30s countdown"
```

---

### Task 6 — `ThreeCanvas`: replace `phase === 'night'` string match

**Files**
- Modify: `frontend/src/components/ThreeCanvas.tsx`
- Test: `frontend/src/components/ThreeCanvas.test.tsx`

> `ThreeCanvas` renders a WebGL `<Canvas>` which jsdom cannot run, so the test extracts and asserts the pure night/day decision via `isNightPhase` rather than rendering the scene. The component change itself is small and mechanical.

- [ ] Write the failing test `frontend/src/components/ThreeCanvas.test.tsx`:
```tsx
import { describe, expect, it } from "vitest";
import { isNightPhase } from "../lib/api";
import { GamePhase } from "../types";

// ThreeCanvas night logic must come from isNightPhase(gameState.phase),
// never from a literal `phase === "night"` string comparison.
describe("ThreeCanvas night derivation", () => {
  it("matches isNightPhase for every GamePhase", () => {
    expect(isNightPhase(GamePhase.night)).toBe(true);
    expect(isNightPhase(GamePhase.setup)).toBe(true);
    expect(isNightPhase(GamePhase.sheriff_election)).toBe(false);
    expect(isNightPhase(GamePhase.day_discussion)).toBe(false);
    expect(isNightPhase(GamePhase.day_voting)).toBe(false);
    expect(isNightPhase(GamePhase.ended)).toBe(false);
  });
});
```

- [ ] Run it, verify it PASSES already (this guards the predicate; the real change is enforced by lint below):
```bash
cd frontend && npx vitest run src/components/ThreeCanvas.test.tsx
```
Expected: `Tests  1 passed (1)`.

- [ ] Confirm the current `ThreeCanvas.tsx` fails the type check because it still reads `snapshot` (removed from the store in Task 4):
```bash
cd frontend && npm run lint
```
Expected: errors like `src/components/ThreeCanvas.tsx ... Property 'snapshot' does not exist on type 'GameStore'`.

- [ ] In `frontend/src/components/ThreeCanvas.tsx`, update the import line to pull the predicate and phase enum:
```tsx
import { useGameStore } from "../store";
import { GamePhase } from "../types";
import { isNightPhase } from "../lib/api";
```

- [ ] In `CameraTracker`, replace the `snapshot` reads with `gameState`:
```tsx
  const gameState = useGameStore((state) => state.gameState);
  const status = useGameStore((state) => state.status);
  const currentSpeakerSeat = useCurrentSpeakerSeat();

  const players = gameState?.players || [];
  const phase = gameState?.phase ?? GamePhase.setup;
```

- [ ] In the `ThreeCanvas` component body, replace the `snapshot`/string-match block:
```tsx
  const gameState = useGameStore((state) => state.gameState);
  const status = useGameStore((state) => state.status);
  const currentSpeakerSeat = useCurrentSpeakerSeat();

  const phase = gameState?.phase ?? GamePhase.setup;
  // Single authoritative night/day decision — no string matching.
  const isNight = isNightPhase(phase) || status === "idle";
```

- [ ] Update the `previewPlayers` memo to use `gameState` instead of `snapshot`:
```tsx
  const previewPlayers = React.useMemo(() => {
    if (status === "idle" || !gameState) {
      return Array.from({ length: 6 }, (_, idx) => ({
        seat: idx + 1,
        name: `席位 ${idx + 1}`,
        is_alive: true,
        isSpeaking: false,
      }));
    }
    return (gameState.players || []).map((p) => ({
      seat: p.seat,
      name: p.name,
      is_alive: p.is_alive,
      isSpeaking: currentSpeakerSeat === p.seat,
    }));
  }, [status, gameState, currentSpeakerSeat]);
```

- [ ] Re-run the canvas test and confirm `ThreeCanvas` no longer trips the type check for `snapshot`:
```bash
cd frontend && npx vitest run src/components/ThreeCanvas.test.tsx
```
Expected: the canvas test passes. (Type-checking is gated project-wide by `npm run lint` at this milestone's final verification step — a single-file `tsc --noEmit` bypasses the project tsconfig/jsx/paths settings, so we don't rely on it per-file here.)

- [ ] Commit:
```bash
git add frontend/src/components/ThreeCanvas.tsx frontend/src/components/ThreeCanvas.test.tsx && git commit -m "feat(frontend): ThreeCanvas night derived from isNightPhase(gameState.phase)"
```

---

### Task 7 — `ControlPanel`: wire pause/resume/single-step/speed to `/control`

**Files**
- Modify: `frontend/src/components/ControlPanel.tsx`
- Test: `frontend/src/components/ControlPanel.test.tsx`

- [ ] Write the failing test `frontend/src/components/ControlPanel.test.tsx`:
```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ControlPanel from "./ControlPanel";
import { useGameStore } from "../store";

afterEach(() => { useGameStore.getState().exitToSetup(); vi.restoreAllMocks(); });

describe("ControlPanel", () => {
  it("pause button calls controlGame('pause') when playing", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "running", playState: "playing", runId: "r1", controlGame: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("暂停"));
    expect(spy).toHaveBeenCalledWith("pause");
  });

  it("shows 继续 and calls controlGame('resume') when paused", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "paused", playState: "paused", runId: "r1", controlGame: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("继续"));
    expect(spy).toHaveBeenCalledWith("resume");
  });

  it("single-step button calls stepGame()", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "running", playState: "playing", runId: "r1", stepGame: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("单步"));
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("speed buttons are 1x/2x/4x and call setSpeed", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "running", playState: "playing", runId: "r1", speed: 1, setSpeed: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("4x"));
    expect(spy).toHaveBeenCalledWith(4);
    expect(screen.queryByText("瞬间")).not.toBeInTheDocument();
  });
});
```

- [ ] Run it, verify it FAILS:
```bash
cd frontend && npx vitest run src/components/ControlPanel.test.tsx
```
Expected: fails — there is no "单步" button, speed shows "瞬间"/999, and it still uses local `togglePlay`/`isPlaying` (no `controlGame`/`stepGame`).

- [ ] Replace the whole contents of `frontend/src/components/ControlPanel.tsx`:
```tsx
import React from "react";
import { useGameStore } from "../store";
import { Play, Pause, SkipForward, Square, Eye, EyeOff, Gauge } from "lucide-react";
import { GamePhase } from "../types";

export default function ControlPanel() {
  const playState = useGameStore((s) => s.playState);
  const speed = useGameStore((s) => s.speed);
  const revealView = useGameStore((s) => s.revealView);
  const gameState = useGameStore((s) => s.gameState);
  const status = useGameStore((s) => s.status);
  const controlGame = useGameStore((s) => s.controlGame);
  const stepGame = useGameStore((s) => s.stepGame);
  const setSpeed = useGameStore((s) => s.setSpeed);
  const setRevealView = useGameStore((s) => s.setRevealView);
  const cancelGame = useGameStore((s) => s.cancelGame);

  const ended =
    gameState?.phase === GamePhase.ended || status === "cancelled" || status === "error";
  const isPlaying = playState === "playing";

  return (
    <div className="bg-transparent border-t border-zinc-900/35 px-6 py-3 flex flex-wrap items-center justify-center gap-4 relative z-10 shrink-0 select-none min-h-[64px]">
      <button onClick={() => controlGame(isPlaying ? "pause" : "resume")} disabled={ended}
        className={`stone-btn px-5 py-2.5 font-sans font-black text-[#f5f5f5] uppercase tracking-widest rounded shadow-lg flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:scale-105 active:translate-y-1"}`}>
        {isPlaying ? <Pause className="w-4 h-4 text-yellow-500" /> : <Play className="w-4 h-4 text-emerald-500" />}
        {isPlaying ? "暂停" : "继续"}
      </button>

      <button onClick={() => stepGame()} disabled={ended}
        className={`px-4 py-2.5 rounded border border-zinc-800 bg-zinc-950/30 text-zinc-200 font-sans font-black text-xs uppercase tracking-widest flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:text-white hover:border-zinc-600"}`}>
        <SkipForward className="w-4 h-4 text-emerald-400" /> 单步
      </button>

      <div className="flex items-center gap-1.5 bg-zinc-950/30 px-3 py-1.5 rounded border border-zinc-900/50">
        <Gauge className="w-3.5 h-3.5 text-zinc-400" />
        {[1, 2, 4].map((s) => (
          <button key={s} onClick={() => setSpeed(s as 1 | 2 | 4)} disabled={ended}
            className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded ${speed === s ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500" : "text-zinc-400 border border-zinc-800 hover:text-zinc-200"}`}>
            {s}x
          </button>
        ))}
      </div>

      <button onClick={() => setRevealView(revealView === "god" ? "suspense" : "god")}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-950/30 text-[11px] font-mono font-bold text-zinc-300 hover:text-white">
        {revealView === "god" ? <Eye className="w-3.5 h-3.5 text-yellow-500" /> : <EyeOff className="w-3.5 h-3.5 text-zinc-400" />}
        {revealView === "god" ? "上帝视角" : "悬念模式"}
      </button>

      <button onClick={cancelGame} disabled={ended}
        className={`px-4 py-2 rounded border-2 border-red-950 bg-red-900 text-red-100 font-sans font-black text-xs uppercase tracking-widest flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:bg-red-700"}`}>
        <Square className="w-3.5 h-3.5" /> 停止
      </button>

      {ended && <span className="font-mono text-[11px] text-zinc-400 uppercase tracking-widest">对局已结束</span>}
    </div>
  );
}
```

- [ ] Run the test, verify it PASSES:
```bash
cd frontend && npx vitest run src/components/ControlPanel.test.tsx
```
Expected: `Tests  4 passed (4)`.

- [ ] Commit:
```bash
git add frontend/src/components/ControlPanel.tsx frontend/src/components/ControlPanel.test.tsx && git commit -m "feat(frontend): ControlPanel wires pause/resume/single-step/speed(1|2|4) to /control"
```

---

### Task 8 — `SpeechConsole`: structured skill/vote/death rows + sub-phase banner

**Files**
- Modify: `frontend/src/components/SpeechConsole.tsx`
- Test: `frontend/src/components/SpeechConsole.test.tsx`

- [ ] Write the failing test `frontend/src/components/SpeechConsole.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import SpeechConsole from "./SpeechConsole";
import { useGameStore } from "../store";
import { GamePhase, GameStateResponse, RenderLog } from "../types";

function withLogs(logs: RenderLog[], state?: Partial<GameStateResponse>) {
  const base: GameStateResponse = {
    status: "running", error: null, play_state: "playing", speed: 1,
    phase: GamePhase.night, sub_phase: null, round: 1, current_actor_seat: null,
    winner: null, sheriff_seat: null, alive_count: 6, dead_count: 0,
    last_night: null, votes: null, cursor: 0, players: [],
  };
  useGameStore.setState({ logs, gameState: { ...base, ...state } });
}

afterEach(() => useGameStore.getState().exitToSetup());

describe("SpeechConsole structured rendering", () => {
  it("renders a death row distinctly from speech", () => {
    withLogs([{ seq: 1, kind: "death", round: 1, speakerSeat: 7, speakerName: "", text: "出局：7号（wolf_kill）", visibility: "public" }]);
    render(<SpeechConsole />);
    expect(screen.getByText("出局：7号（wolf_kill）")).toBeInTheDocument();
  });

  it("renders a skill row", () => {
    withLogs([{ seq: 2, kind: "skill", round: 1, speakerSeat: 1, speakerName: "", text: "技能：seer_check（1号 → 3号）", visibility: "god" }]);
    render(<SpeechConsole />);
    expect(screen.getByText("技能：seer_check（1号 → 3号）")).toBeInTheDocument();
  });

  it("shows the sub-phase highlight banner", () => {
    withLogs([], { sub_phase: "witch_decide" });
    render(<SpeechConsole />);
    expect(screen.getByText("女巫决策中")).toBeInTheDocument();
  });
});
```

- [ ] Run it, verify it FAILS:
```bash
cd frontend && npx vitest run src/components/SpeechConsole.test.tsx
```
Expected: fails — `SpeechConsole` still reads `snapshot.phase_label` (removed) and `log.day`, so it does not compile/render; the sub-phase banner does not exist.

- [ ] Replace the whole contents of `frontend/src/components/SpeechConsole.tsx`:
```tsx
import React, { useEffect, useRef } from "react";
import { MessageSquare, Scroll, Brain, Activity } from "lucide-react";
import { useGameStore } from "../store";
import { RenderLog, SUB_PHASE_LABELS, PHASE_LABELS, GamePhase } from "../types";

interface SpeechConsoleProps {
  isExpanded?: boolean;
  onToggle?: () => void;
}

function EventRow({ log }: { log: RenderLog }) {
  // 非发言事件（skill / vote / death / phase / system）：居中系统行
  if (log.kind !== "speech") {
    const tone =
      log.kind === "death" ? "text-red-400 border-red-900/60"
      : log.kind === "vote" ? "text-yellow-400 border-yellow-900/50"
      : log.kind === "skill" ? "text-fuchsia-300 border-fuchsia-900/50"
      : log.kind === "phase" || log.kind === "sub_phase" ? "text-zinc-300 border-zinc-700"
      : "text-zinc-400 border-zinc-800";
    return (
      <div className="flex justify-center my-2">
        <div className={`bg-black/70 border px-3 py-1 rounded text-center max-w-[85%] ${tone}`}>
          <p className="font-mono text-[11px] font-bold">{log.text}</p>
        </div>
      </div>
    );
  }
  // 发言气泡 + 内心 OS
  return (
    <div className="flex gap-3 max-w-[90%] mr-auto">
      <div className="w-10 h-10 rounded shrink-0 flex flex-col items-center justify-center font-mono font-black text-xs shadow-md bg-black border-2 border-zinc-800 text-zinc-300">
        <span className="text-[10px] opacity-60">P</span>
        <span className="text-sm -mt-1">{log.speakerSeat ?? "?"}</span>
      </div>
      <div className="relative px-7 py-4 rounded-lg border-2 shadow-2xl parchment font-serif max-w-lg rounded-tl-none">
        <div className="flex items-center justify-between gap-6 border-b border-black/20 pb-1.5 mb-2 font-mono text-[9px] font-black uppercase tracking-wider text-black">
          <span className="text-blue-900">{log.speakerName || `玩家 ${log.speakerSeat}`}</span>
          <span className="text-zinc-700 tracking-widest">ROUND {log.round}</span>
        </div>
        <p className="text-[12.5px] leading-relaxed font-sans font-extrabold whitespace-pre-wrap text-[#1a1a1a]">
          {log.text}
        </p>
        {log.privateThought && (
          <div className="mt-2 pt-2 border-t border-dashed border-black/30 bg-fuchsia-950/10 -mx-3 px-3 rounded">
            <span className="flex items-center gap-1 font-mono text-[8px] uppercase tracking-widest text-fuchsia-800 font-black mb-0.5">
              <Brain className="w-3 h-3" /> 内心 OS（上帝视角）
            </span>
            <p className="text-[11px] italic text-fuchsia-950/90 whitespace-pre-wrap">{log.privateThought}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SpeechConsole({ isExpanded = true, onToggle }: SpeechConsoleProps) {
  const logs = useGameStore((s) => s.logs);
  const gameState = useGameStore((s) => s.gameState);
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isExpanded) listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, isExpanded]);

  const phase = gameState?.phase ?? GamePhase.setup;
  const subPhaseLabel = gameState?.sub_phase ? SUB_PHASE_LABELS[gameState.sub_phase] ?? gameState.sub_phase : null;
  const narration = subPhaseLabel ?? PHASE_LABELS[phase] ?? "幽暗城堡的丧钟敲响，AI 们各就各位...";

  return (
    <div className="flex flex-col flex-grow bg-transparent overflow-hidden relative z-10">
      <div className="flex items-center justify-between bg-transparent px-4 py-1.5 border-b border-zinc-900/50 select-none">
        <div className="flex items-center gap-2">
          <Scroll className="w-4 h-4 text-red-600 animate-pulse" />
          <span className="font-sans font-black text-xs tracking-widest text-zinc-100 uppercase ink-shadow">⚖ AI 审判会议实录 ⚖</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-[9px] text-[#e0e0e0]/70">
            <MessageSquare className="w-3.5 h-3.5 text-yellow-500" />
            <span>共 {logs.length} 条</span>
          </div>
          {onToggle && (
            <button onClick={onToggle} className="flex items-center gap-1.5 px-2.5 py-1 bg-black/30 hover:bg-black/60 border border-zinc-800 rounded text-[10px] text-zinc-300 font-mono font-black uppercase tracking-widest cursor-pointer">
              {isExpanded ? "收起 ▼" : "展开 ▲"}
            </button>
          )}
        </div>
      </div>

      {/* Sub-phase highlight banner (狼人夜聊中 / 女巫决策中 / 预言家查验中) */}
      <div className="bg-transparent p-3 border-b border-zinc-900/30 flex gap-3 items-start">
        <div className="w-8 h-8 rounded shrink-0 bg-red-950/40 border border-red-800/60 flex items-center justify-center text-red-500 font-serif font-black text-sm animate-pulse">
          {subPhaseLabel ? <Activity className="w-4 h-4 text-fuchsia-400" /> : "☠"}
        </div>
        <p className="font-sans text-xs text-[#e0e0e0] leading-relaxed font-black font-serif">{narration}</p>
      </div>

      <div className="flex-grow overflow-y-auto px-4 py-4 space-y-3 font-sans select-text bg-transparent">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-600 gap-2 py-8">
            <span className="font-serif text-4xl text-zinc-800 animate-pulse">☠</span>
            <span className="font-mono text-xs tracking-widest text-zinc-700 uppercase font-black">等待 AI 入场…</span>
          </div>
        ) : (
          logs.map((log) => <EventRow key={log.seq} log={log} />)
        )}
        <div ref={listEndRef} />
      </div>
    </div>
  );
}
```

- [ ] Run the test, verify it PASSES:
```bash
cd frontend && npx vitest run src/components/SpeechConsole.test.tsx
```
Expected: `Tests  3 passed (3)`.

- [ ] Commit:
```bash
git add frontend/src/components/SpeechConsole.tsx frontend/src/components/SpeechConsole.test.tsx && git commit -m "feat(frontend): SpeechConsole structured skill/vote/death rows + sub-phase banner"
```

---

### Task 9 — `App` + `CardDeck`: single game-over signal (phase === 'ended')

**Files**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/CardDeck.tsx`
- Test: `frontend/src/components/CardDeck.test.tsx`

- [ ] Write the failing test `frontend/src/components/CardDeck.test.tsx` (covers the reveal logic moved off `snapshot.winner`):
```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import CardDeck from "./CardDeck";
import { useGameStore } from "../store";
import { GamePhase, GameStateResponse } from "../types";

function setState(partial: Partial<GameStateResponse>, revealView: "god" | "suspense" = "suspense") {
  const base: GameStateResponse = {
    status: "running", error: null, play_state: "playing", speed: 1,
    phase: GamePhase.night, sub_phase: null, round: 1, current_actor_seat: null,
    winner: null, sheriff_seat: null, alive_count: 1, dead_count: 0,
    last_night: null, votes: null, cursor: 0,
    players: [{ seat: 1, name: "Alice", role: "狼人", camp: "wolf", is_alive: true, is_sheriff: false, model: "deepseek-chat", status_flags: ["alive"] }],
  };
  useGameStore.setState({ gameState: { ...base, ...partial }, revealView });
}

afterEach(() => useGameStore.getState().exitToSetup());

describe("CardDeck reveal", () => {
  it("hides role in suspense mode mid-game", () => {
    setState({ phase: GamePhase.night });
    render(<CardDeck />);
    expect(screen.getByText("未知秘匿")).toBeInTheDocument();
    expect(screen.queryByText("狼人")).not.toBeInTheDocument();
  });

  it("reveals role when phase === 'ended' (no snapshot.winner)", () => {
    setState({ phase: GamePhase.ended, winner: "wolf" });
    render(<CardDeck />);
    expect(screen.getByText("狼人")).toBeInTheDocument();
  });
});
```

- [ ] Run it, verify it FAILS:
```bash
cd frontend && npx vitest run src/components/CardDeck.test.tsx
```
Expected: fails — `CardDeck` reads `snapshot` (removed) and reveals on `snapshot?.winner`, so it does not compile/behave correctly.

- [ ] In `frontend/src/components/CardDeck.tsx`, update the import line and the data reads at the top of `CardDeck`:
```tsx
import React from "react";
import { useGameStore } from "../store";
import { GamePhase } from "../types";
```

- [ ] Replace the `CardDeck` data-read lines:
```tsx
export default function CardDeck() {
  const gameState = useGameStore((s) => s.gameState);
  const revealView = useGameStore((s) => s.revealView);
  const players = gameState?.players || [];
  const isEnded = gameState?.phase === GamePhase.ended;
```

- [ ] Replace the per-player reveal predicate (was `revealView === "god" || !p.is_alive || !!snapshot?.winner`):
```tsx
          // 上帝视角：始终亮身份；悬念模式：仅死亡或终局亮身份
          const isExposed = revealView === "god" || !p.is_alive || isEnded;
```

- [ ] Run the CardDeck test, verify it PASSES:
```bash
cd frontend && npx vitest run src/components/CardDeck.test.tsx
```
Expected: `Tests  2 passed (2)`.

- [ ] In `frontend/src/App.tsx`, update the imports and store reads to use `gameState`:
```tsx
import { useGameStore } from "./store";
import { GamePhase } from "./types";
```

- [ ] Replace the App store reads + setup gate:
```tsx
  const gameState = useGameStore((state) => state.gameState);
  const status = useGameStore((state) => state.status);
  const exitToSetup = useGameStore((state) => state.exitToSetup);
```

- [ ] Replace the `inSetup` line (status values are now `running|paused|ended|cancelled|error`):
```tsx
  // 未开局（idle）显示开局配置页
  const inSetup = status === "idle" || (!gameState && status !== "running");
```

- [ ] Replace the GameOver overlay block so it is keyed solely on `phase === 'ended'`:
```tsx
      {/* GameOver Panel Overlay — single signal: phase === "ended" */}
      {gameState?.phase === GamePhase.ended && (
        <GameOverPanel winner={gameState.winner ?? ""} onExit={exitToSetup} />
      )}
```

- [ ] Run the full frontend test suite — everything green:
```bash
cd frontend && npx vitest run
```
Expected: all test files pass (`setup.smoke`, `types`, `lib/api`, `store`, `TopHeader`, `ThreeCanvas`, `ControlPanel`, `SpeechConsole`, `CardDeck`).

- [ ] Type-check the whole project — must be clean now that every consumer of the old `snapshot`/`day`/`phase_label` is migrated:
```bash
cd frontend && npm run lint
```
Expected: no output, exit code 0.

- [ ] Commit:
```bash
git add frontend/src/App.tsx frontend/src/components/CardDeck.tsx frontend/src/components/CardDeck.test.tsx && git commit -m "feat(frontend): single game-over signal (phase==='ended') in App + CardDeck reveal"
```

---

### Task 10 — Verify SSE survives the Vite dev proxy (no buffering) + production build

**Files**
- Modify: `frontend/vite.config.ts`
- Test (manual gate, documented inline): N/A — verified via build + a dev-proxy smoke run

> Spec §11 risk: *"SSE through the Vite dev proxy must not buffer the stream (disable response buffering / compression for `text/event-stream`); verify in dev."* The current proxy block has no SSE handling.

- [ ] In `frontend/vite.config.ts`, replace the `/api/v1` proxy entry so SSE is not buffered (disable proxy timeout + ensure the upstream stream is piped unbuffered):
```ts
      proxy: {
        "/api/v1": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          // SSE: keep the upstream stream open and unbuffered.
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq, req) => {
              if (req.url?.endsWith("/stream")) {
                proxyReq.setHeader("Accept", "text/event-stream");
                proxyReq.setHeader("Cache-Control", "no-cache");
              }
            });
            proxy.on("proxyRes", (proxyRes, req) => {
              if (req.url?.endsWith("/stream")) {
                proxyRes.headers["cache-control"] = "no-cache";
                delete proxyRes.headers["content-length"];
              }
            });
          },
        },
      },
```

- [ ] Type-check still passes (vite config is part of the build graph):
```bash
cd frontend && npm run lint
```
Expected: no output, exit code 0.

- [ ] Production build succeeds (catches any remaining type/import regressions the lint step's `noEmit` might mask in the bundler):
```bash
cd frontend && npm run build
```
Expected: `vite build` completes with `✓ built in …` and writes `dist/`; the esbuild `server.ts` bundle step also completes.

- [ ] Manual dev-proxy SSE smoke (documented; run when the Python backend from M1–M4 is up on :8000). Start the spectate dev server and a game, then confirm events arrive incrementally rather than in one buffered flush:
```bash
cd frontend && npm run dev:spectate
```
Expected: in the browser network panel the `/api/v1/games/{id}/stream` request stays in "pending"/open with `id:`/`event:`/`data:` chunks streaming in over time (not a single buffered response at the end); the speech log fills incrementally and pause/resume/single-step change `play_state` immediately.

- [ ] Commit:
```bash
git add frontend/vite.config.ts && git commit -m "fix(frontend): disable Vite proxy buffering for SSE /stream"
```

---

### Milestone verification (final gate)

- [ ] Full test suite + type check + build all green from a clean tree:
```bash
cd frontend && npx vitest run && npm run lint && npm run build
```
Expected: all vitest files pass; `tsc --noEmit` emits nothing; `vite build` succeeds. No remaining references to the removed fakes — confirm with a search that the deletions stuck:
```bash
cd frontend && npx tsc --noEmit
```
Expected: clean. (Manual confirmation that `localSecondsLeft`, `.startsWith("night")`, `=== "night"` string-matches, `snapshot.winner` dual-signal, the 1000ms `POLL_MS`, and the `/view?since=` poll are all gone.)
