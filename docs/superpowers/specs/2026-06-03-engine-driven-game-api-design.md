# Engine-Driven Game API — Design Spec

**Date:** 2026-06-03
**Branch / worktree:** `feat/engine-driven-api` (`.claude/worktrees/engine-driven-api`)
**Status:** Approved design, pending spec review → implementation plan

---

## 1. Goal

Make the spectator API **engine-driven** instead of **log-driven**: day/night phases, werewolf night chat, and every skill (wolf kill, witch save, seer check, guard, hunter, …) are surfaced from the game engine's authoritative live state and structured signals — not reverse-engineered by parsing `events.jsonl`. The spectate experience becomes **controllable** (pause / resume / single-step / speed) and **robust** (survives refresh/disconnect, never loses night results, never blanks on error).

## 2. Background — why today is "log-driven"

The engine is already a clean state machine, but the API throws it away and reads its shadow on disk.

- `_run_game` builds the engine as a **local variable**, runs the whole game with one `await engine.play_game()`, and drops the engine on return. `GameSession` has **no `engine` field** (`interface/api/services/game_sessions.py:99-115`, `:240-251`).
- Every event flows through one choke point, `GameEngineBase._log_event`, which then calls `self.on_event(event)` (`game_runtime/engine/base.py:385-423`). The API wires `on_event` to `IncrementalEventWriter`, which appends each event as a JSONL line to `events.jsonl` (`game_sessions.py:125-127`, `:245-246`). **This disk writer is the only consumer of live engine signal.**
- Read endpoints never touch the engine. `build_view(run_dir)` re-reads `events.jsonl` + `roster.json` on every call and **reverse-engineers** phase, alive/dead, sheriff, winner by replaying rows; phase is taken from **the last event row's `phase` field** (`interface/api/services/view.py:128-182`, esp. `:146`). `/status` likewise rebuilds its snapshot from disk via `extract_game_snapshot` (`game_sessions.py:292-339`; `interface/api/services/replay.py:192-222`).

**The single structural blocker is plumbing:** the engine reference is not retained. Everything else needed for an engine-driven API already exists.

### What the engine already provides (no rewrite needed)

- **Authoritative phase machine.** `GamePhase(str, Enum)` has exactly 6 members — `setup, night, sheriff_election, day_discussion, day_voting, ended` (`game_runtime/types/enums.py:41-49`) — driven by `GameState.next_phase()` (`game_runtime/state/game_state.py:106-141`).
- **A complete synchronous serializer.** `serialize_game_state(game_state) -> GameStateSnapshot` does one pass over players + a flat field copy, no I/O/LLM, JSON-dumpable (`game_runtime/state/serialization.py:154-192`, `:230-231`). It already covers nearly everything `build_view` reconstructs.
- **A phase-stepper.** `async def step()` runs exactly one phase per call, dispatching on `game_state.get_phase()` and advancing via `next_phase()` (`base.py:567-605`). It exists but is **unused** — the API only calls `play_game()`.

### Gaps the three requirements expose

1. **Phase signals are incomplete.** `phase_changed` is emitted only at `night` and `day_discussion` entry (`game_runtime/engine/night_phase.py:311-315`, `game_runtime/engine/day_phase.py:100-104`). `sheriff_election`, `day_voting`, `setup→night`, and `ended` emit **no** `phase_changed`. A log-only frontend cannot detect those phase starts; live `game_state.phase` can.
2. **Werewolf night chat** is real (`_run_werewolf_discussion`, wolf-only channel; `night_phase.py:146-205`) but surfaces as a generic `player_discussion` row with no dedicated sub-phase marker.
3. **Five skills have no dedicated event type** — White Wolf kill, Wolf Beauty charm, Nightmare block, Guardian Wolf protect, Raven mark — they are generic `message` rows distinguished only by locale text (`game_runtime/engine/action_processor.py:177-236`). The frontend cannot classify them.
4. **Night results are cleared** on `DAY_VOTING→NIGHT` by `next_phase()` (`werewolf_target`, witch targets, `guard_protected`, `votes`, …) and `reset_deaths()` (`game_state.py:81-86`, `:126-139`). A slow disk poll can miss them.
5. **Frontend mirrors the weakness:** phase is string-matched into a binary night/day and two components disagree (`ThreeCanvas` exact `=== 'night'` vs `TopHeader` `.startsWith('night')`); the countdown is a fake local 30s loop; game-over has two unsynchronized signals (`status === 'ended'` vs `snapshot.winner`).

## 3. Decisions (locked during brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Loop model | **Step-driven** — API pumps `engine.step()` one phase at a time with a control gate | Enables pause / resume / single-step / speed; lets the API snapshot **between** phases so night results are captured before they're cleared |
| Transport | **SSE** for the event stream; plain `GET /state`; plain `POST /control` | Real-time push ≈ WebSocket, robustness ≈ polling. Browser `EventSource` auto-reconnects and resends `Last-Event-ID`, which **is** our resume cursor. No WebSocket connection-lifecycle code; passes through the Vite/HTTP proxy as plain HTTP |
| Pause semantics | **Pause truly halts the engine** (not just the display) | Don't waste LLM calls / money running ahead while nobody is watching; makes single-step meaningful |
| Pause granularity | **Phase level** (the 6 phases); sub-phases (wolf chat, witch, seer) are **signal-highlighted** but not pause points | Stepping at every micro-action is fragile; phase-level boundaries are clean and already exist |
| Visibility | **God-view full snapshot + client-side suspense toggle** (unchanged from the prior pure-LLM spectate design) | Keep the already-shipped reveal model; no server-side per-seat fog-of-war |
| Replay / post-game | **Keep writing `events.jsonl`**; finished-game read paths unchanged | Zero impact on replay and the post-game pipeline (which runs from disk with `engine=None`) |

### Non-goals (YAGNI)

- WebSocket transport (revisit only if token-by-token streaming is wanted later — the interface is designed to migrate cleanly).
- Token-by-token "typewriter synced to LLM generation" (engine returns whole speeches today).
- Server-enforced per-seat fog-of-war.
- Human-in-the-loop play (web human games remain unsupported, as today).

## 4. Architecture

```
                         ┌──────────────────────────────────────┐
                         │  GameSession (in-memory, per run_id)  │
 POST /games/start ─────▶│  • engine (RETAINED)                  │
                         │  • control gate (resume Event, step)  │
                         │  • EventHub (in-mem pub/sub)          │
                         └──────────────────────────────────────┘
                                        │ _run_game: while not over: await engine.step()
                                        │            snapshot between phases (pre-clear)
                                        ▼
              engine._log_event ──▶ on_event(event) ──┬──▶ events.jsonl  (disk, replay)
                                                       └──▶ EventHub.publish (in-mem)
                                                                  │
   GET  /games/{id}/state    ◀── serialize_game_state(engine.game_state)   (authoritative)
   GET  /games/{id}/stream   ◀── SSE: EventHub subscribe, resume by Last-Event-ID
   POST /games/{id}/control  ──▶ control gate: pause | resume | step | speed
                                        │
                                        ▼
                         Frontend: EventSource(/stream) + GET /state + control bar
```

### Components

- **`GameSession` (extended)** — gains `engine`, a **control gate**, and an **`EventHub`** reference. Holds the live authority for an in-progress run.
- **Control gate** — an `asyncio.Event` (`set` = playing, `clear` = paused) plus a `step_once` flag. The step-pump loop awaits the gate **between** phases. Default is **playing** (so a run with no connected client still progresses and records to disk). Single-step = run one phase, then auto-clear the gate.
- **`EventHub`** — an in-process publish/subscribe fed by `on_event`. Each event is assigned a monotonic `seq`. Subscribers (one per SSE connection) get a bounded `asyncio.Queue`; new subscribers receive a **backfill from `seq > Last-Event-ID`** so reconnects never miss events. The disk writer remains a parallel sink (one source, two sinks).
- **Live state serializer (extended)** — `serialize_game_state` widened so the spectator snapshot is complete (see §6).
- **Frontend store (rewritten transport)** — `EventSource` subscription replaces the 1s poll; `GET /state` provides authoritative phase + full-snapshot fallback; control bar calls `/control`.

## 5. API contract

All under `/api/v1`. Existing endpoints (`/games/start`, `/games/{id}/cancel`, run listing, replay, status for finished games) are **kept**.

### 5.1 `GET /games/{run_id}/state` — authoritative live snapshot

Served from the live engine when the session is in memory; falls back to disk reconstruction for finished/evicted runs (so old runs and replays keep working).

```jsonc
{
  "status": "running | paused | ended | cancelled | error",
  "error": null,
  "play_state": "playing | paused",
  "speed": 1,                          // 1 | 2 | 4 (inter-phase dwell factor)
  "phase": "night",                    // authoritative GamePhase enum value
  "sub_phase": "werewolf_chat",        // null | werewolf_chat | witch_decide | seer_check | ... (display hint)
  "round": 2,
  "current_actor_seat": 5,             // whose turn, or null
  "winner": null,                      // null until phase == "ended"
  "sheriff_seat": 3,
  "alive_count": 6,
  "dead_count": 2,
  "last_night": {                      // captured BEFORE next_phase() clears it
    "deaths": [{"seat": 7, "cause": "wolf_kill"}],
    "saved_seat": null,
    "guarded_seat": 4,
    "poisoned_seat": null
  },
  "votes": { "by_seat": {"1": 5, "2": 5}, "tally": {"5": 2} },
  "cursor": 142,                       // current max event seq (for resume / display sync)
  "players": [
    {"seat": 1, "name": "...", "role": "Seer", "camp": "good",
     "is_alive": true, "is_sheriff": false, "model": "deepseek-chat",
     "status_flags": ["alive"]}
  ]
}
```

`status` collapses session state + `play_state`: a paused running game reports `"paused"`. `phase` is the **single** authoritative phase; the frontend never string-matches a log row again.

### 5.2 `GET /games/{run_id}/stream` — SSE event stream

`Content-Type: text/event-stream`. Each event:

```
id: 143
event: game
data: {"seq":143,"type":"speech","phase":"day_discussion","sub_phase":null,
       "round":2,"reveal":"now","visibility":"public",
       "speaker":{"seat":3,"name":"..."},"public_text":"...","private_thought":"..."}
```

- `id:` is the monotonic `seq`. On reconnect the browser sends `Last-Event-ID`; the server **backfills** all events with `seq` greater than it, then resumes live — this replaces the `since=N` poll cursor.
- A periodic comment heartbeat (`: keep-alive`) keeps the connection open through idle phases.
- `type ∈ {speech, skill, vote, death, phase, sub_phase, belief, vote_intention, system}`.
- **Structured payloads** (server-authoritative, not string-guessed):
  - `speech`: `speaker {seat,name}`, `public_text`, `private_thought`.
  - `skill`: `kind`, `actor {seat}`, `target {seat}`, `result`. `kind` covers the full set incl. the five formerly-untyped skills: `wolf_kill, white_wolf_kill, wolf_beauty_charm, nightmare_block, guardian_wolf_guard, raven_mark, witch_save, witch_poison, seer_check, guard, graveyard_check, hunter_shoot, badge_transfer`.
  - `vote`: `voter {seat}`, `target {seat}`.
  - `death`: `seat`, `name`, `cause`.
  - `phase`: `phase`, `round` (now emitted for **all** transitions incl. sheriff_election / day_voting / ended).
  - `sub_phase`: `name` (display hint for night sub-steps).
- `reveal ∈ {now, on_death, on_game_end}` and `visibility ∈ {public, wolf, god}` come from the engine's authoritative per-event `visible_to`, not heuristics.

### 5.3 `POST /games/{run_id}/control`

```jsonc
// request
{ "action": "pause" | "resume" | "step" | "speed", "value": 2 }   // value only for "speed"
// response
{ "run_id": "...", "play_state": "paused", "speed": 2, "phase": "night" }
```

- `pause` — clears the control gate; the engine stops at the **end of the current phase** (no mid-phase abort, no orphaned LLM calls beyond the one in flight).
- `resume` — sets the gate.
- `step` — runs exactly one phase then auto-pauses.
- `speed` — sets the inter-phase dwell factor (how long a completed phase lingers before the next starts); `1|2|4`.

## 6. Engine-layer changes (`game_runtime/`)

1. **Retain the engine.** Add `engine` (and the control gate / EventHub wiring) to `GameSession`; set `session.engine = engine` in `_run_game` before the run loop (`game_sessions.py:99-115`, `:240`).
2. **Step-pump loop.** Replace `await engine.play_game()` with:
   ```
   while not engine.is_over():            # phase != ended
       await session.gate.wait()          # honor pause/step
       await engine.step()                # one phase
       session.capture_phase_snapshot()   # snapshot BEFORE next clear
       if session.step_once: session.gate.clear()
       await asyncio.sleep(dwell / speed) # speed control
   ```
3. **Reconcile `step()` with `play_game()`.** Fix the known divergences so stepping is byte-for-byte equivalent to the autonomous loop: call `reset_deaths()` at NIGHT entry; remove the SETUP placeholder strings; ensure `check_victory()` (which has side effects — sets `phase=ENDED`, `winner`, emits `GAME_ENDED`, calls `memory_manager.on_game_end`, `base.py:251-285`) is invoked at the same boundaries and **exactly once** (no double `GAME_ENDED`).
4. **Capture night results before clearing.** Snapshot `night_deaths/day_deaths/death_causes/werewolf_target/witch_*/guard_protected/votes` between phases (they're cleared by `next_phase()` on `DAY_VOTING→NIGHT`, `game_state.py:126-139`). Surface them as `last_night` in `/state`.
5. **Emit the missing phase signals.** Add `phase_changed` at `sheriff_election`, `day_voting`, `setup→night`, and `ended` entry (today only night/day_discussion emit it).
6. **Add sub-phase signals.** Emit a lightweight `sub_phase` event at the boundaries the engine already has (`NightSkillScheduler.run_pre_wolf_phase / run_wolf_vote_phase / run_post_wolf_resolution`, `game_runtime/night_scheduler.py:61-74`, and `_run_werewolf_discussion`): `werewolf_chat`, `witch_decide`, `seer_check`, etc. Pure display hints; they are not `GamePhase` members and not pause points.
7. **Give the five untyped skills dedicated structured events.** White Wolf kill, Wolf Beauty charm, Nightmare block, Guardian Wolf protect, Raven mark — emit typed events with `{actor, target, result}` instead of generic `message` rows (`action_processor.py:177-236`).
8. **Widen the snapshot.** Extend `_extract_role_data`'s allowlist so Hunter / Seer (and future roles) serialize their skill state instead of empty `role_data` (`serialization.py:108-129`); add `sub_phase`, `current_actor_seat`, and `last_night` to the snapshot shape (or compose them in the API layer from live state).
9. **One source, two sinks.** Keep `IncrementalEventWriter` (disk) and add `EventHub.publish` as a second `on_event` sink. A tiny fan-out wrapper calls both. Disk format is unchanged → replay/post-game untouched.

## 7. Frontend changes (`frontend/src/`)

1. **Authoritative phase.** Read `phase` (+ `sub_phase`, `round`, `winner`, `play_state`) from `GET /state`; drive all UI off the `GamePhase` enum. Delete the string-matching in `ThreeCanvas`/`TopHeader`, the fake 30s countdown, and the dual game-over signals — game-over is solely `phase === "ended"`.
2. **SSE transport.** Replace the 1000ms poll + 220ms drain with an `EventSource` on `/stream`; rely on built-in reconnect + `Last-Event-ID`. Keep a small render buffer so bursts within a phase stay readable; `speed` now also maps to `/control`.
3. **Control bar.** Pause / Resume / Single-step / Speed → `POST /control`; reflect `play_state` from `/state`.
4. **Structured rendering.** Render `ev.skill` / `ev.vote` / `ev.death` structurally (the types already exist in `types.ts` but nothing renders them today); show sub-phase highlight (`狼人夜聊中 / 女巫决策中 / 预言家查验中`).
5. **Suspense toggle** unchanged: client masks `visibility === "god"` events until their `reveal` condition, exactly as in the shipped design.

## 8. Robustness & failure handling

- **Engine error** → session `status = "error"`, message surfaced in `/state` and as a terminal SSE `system` event; the frontend shows it instead of blanking.
- **Refresh / disconnect** → `EventSource` auto-reconnects with `Last-Event-ID`; the server backfills missed `seq`s from the EventHub (in-memory) or, if the session was evicted, from `events.jsonl`. `GET /state` always returns a complete snapshot as a fallback.
- **Pause** truly halts the engine → no wasted LLM spend; resume continues deterministically.
- **Night results never lost** → captured between phases before `next_phase()` clears them.
- **Server-authoritative classification & visibility** → the frontend never guesses event type or reveal/visibility, eliminating drift and the snapshot-vs-log race (snapshot and stream share the `cursor`/`seq`).
- **`events.jsonl` preserved** → replay and the post-game pipeline are unaffected.

## 9. Testing strategy

Backend (pytest; repo threshold is high coverage):

- `serialize_game_state` round-trip completeness: every field `build_view` reconstructed is present and correct mid-game, including widened `role_data` for Hunter/Seer.
- `step()` ≡ `play_game()` equivalence: a seeded/mock-LLM game produces the **same** final state, deaths, winner, and event sequence whether run via `play_game()` or the step-pump; `GAME_ENDED` fires exactly once.
- `last_night` capture: night results are present in `/state` after the night phase and before they are cleared.
- Missing phase signals: `phase_changed` is emitted for sheriff_election / day_voting / ended.
- Five skill events: each formerly-untyped skill now emits a typed `skill` event with actor/target.
- `EventHub`: backfill from `Last-Event-ID` returns exactly the missed `seq`s in order; two subscribers each get the full stream; disk sink still receives every event.
- Control gate: `pause` halts after the current phase; `step` advances exactly one phase; `resume` continues; `speed` changes dwell.
- `/state` fallback: a finished/evicted run still returns a correct snapshot from disk.

Frontend: `npm run lint` clean; phase-driven rendering and control wiring verified against a mock SSE stream.

## 10. Rollout

Single feature branch (`feat/engine-driven-api`), but implemented in dependency order so each milestone is independently testable:

1. **Retain engine + `/state`** (live serialization, fallback) — authoritative phase with zero loop change.
2. **Step-pump + control gate + `last_night` capture** — reconcile `step()`, add `/control`.
3. **Engine signals** — missing `phase_changed`, sub-phase events, five typed skill events, widened `role_data`.
4. **EventHub + SSE `/stream`** — one-source-two-sinks, backfill/resume.
5. **Frontend** — SSE transport, phase-driven UI, control bar, structured rendering, remove fakes.

`events.jsonl`, replay, post-game, and the finished-game read paths remain backward-compatible throughout.

## 11. Risks & open points

- **`step()` reconciliation** is the highest-risk change (game-logic equivalence). Mitigated by the equivalence test in §9 before anything depends on it.
- **`check_victory()` side effects** must be triggered through the engine, never replicated, to avoid double `GAME_ENDED` / double `on_game_end`.
- **SSE through the Vite dev proxy** must not buffer the stream (disable response buffering / compression for `text/event-stream`); verify in dev.
- **Speed semantics** are intentionally simple (inter-phase dwell); intra-phase pacing is LLM-bound and left to the small client render buffer.
