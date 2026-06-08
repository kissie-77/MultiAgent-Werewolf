# Camera / Board Re-center Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After every speech and on every phase boundary, the live-game camera cuts back to one canonical wide "home" framing where all seats are visible, holds it briefly, then eases back in — so it never lingers face-locked on a single piece.

**Architecture:** Extract all camera-target math into a pure, unit-tested module `frontend/src/lib/cameraDirector.ts` (`homePose` / `speakerPose` / `decideCamera` decision machine). `ThreeCanvas`'s `CameraTracker` keeps only the thin imperative shell: refs + timers that latch a "wide window" on phase-change and speech-end, then per-frame it asks `decideCamera` for a target pose + damping lambda and `THREE.MathUtils.damp`s toward it. Lobby (START_SCREEN) keeps its existing bespoke slow-orbit untouched.

**Tech Stack:** React 19 + TypeScript, @react-three/fiber (R3F) + three, `motion/react` (`useReducedMotion`), vitest (node env, pure-function tests).

---

## Spec → Task Map

The resolved spec (from the grilling interview) and where each piece is implemented:

| Spec decision | Task |
|---|---|
| **Model A**: focus during speech, **fast cut to wide + ~0.7s hold** after speech ends (overriding even a freshly-arrived next speaker), then **slow push-in** | Task 1 (`decideCamera` precedence + lambdas), Task 2 (`recenterUntilRef` latch) |
| **Home framing** unified to `[0, r*1.85, r*2.6]` look `[0,0.4,0]`, used for hold + establish + initial camera | Task 1 (`homePose`), Task 2 (initial `<Canvas camera>` + ref seed) |
| **Speaker shot softened** to 3/4 mid-shot `[sX*1.25, r*1.45, sZ*1.25]`, look `[sX*0.5, 0.6, sZ*0.5]` | Task 1 (`speakerPose`) |
| **Triggers**: (1) every speech end → wide hold; (2) **any** `gameState.phase` change (coarse day/night + vote/警长/夜技能 sub-phases) → wide establish beat | Task 2 (two `useEffect` latches) |
| **Motion feel**: fast pull (high λ) → hold → slow push (low λ) | Task 1 (`FAST_LAMBDA` / `SLOW_LAMBDA`) |
| **Reduced motion**: never push in on a speaker | Task 1 (`reducedMotion` flag), Task 2 (`useReducedMotion`) |
| **Scope**: live only (Replay never mounts `ThreeCanvas`) | inherent — no code needed |

---

## File Structure

- **Create `frontend/src/lib/cameraDirector.ts`** — pure camera math + the `decideCamera` decision machine. One responsibility: "given game state + timers, what pose and how fast." No three.js / React imports, so it's node-testable.
- **Create `frontend/src/lib/cameraDirector.test.ts`** — vitest unit tests for the pure module.
- **Modify `frontend/src/components/ThreeCanvas.tsx`** — replace the body of `CameraTracker` (lines ~78–190) to drive off `decideCamera`; add three imports; bump the initial camera position and the `targetCamPos` seed to the new home. Lobby orbit branch preserved verbatim.

No other files change. The coarse-stage card/flash system (`stageFx`, `PhaseTransitionCard`) is intentionally left alone — the camera no longer depends on `stageFx`.

---

## Task 1: Pure camera director module

**Files:**
- Create: `frontend/src/lib/cameraDirector.ts`
- Test: `frontend/src/lib/cameraDirector.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/cameraDirector.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  tableRadius,
  homePose,
  speakerPose,
  decideCamera,
  RECENTER_HOLD_MS,
  FAST_LAMBDA,
  SLOW_LAMBDA,
} from "./cameraDirector";

describe("tableRadius", () => {
  it("floors at 5 and scales with seat count", () => {
    expect(tableRadius(6)).toBe(5); // 6*0.72=4.32 -> floored to 5
    expect(tableRadius(7)).toBeCloseTo(5.04, 5);
    expect(tableRadius(8)).toBeCloseTo(5.76, 5);
    expect(tableRadius(10)).toBeCloseTo(7.2, 5);
  });
});

describe("homePose", () => {
  it("is a centered, pulled-back overview", () => {
    const { pos, look } = homePose(6); // r=5
    expect(pos).toEqual([0, 9.25, 13]); // [0, r*1.85, r*2.6]
    expect(look).toEqual([0, 0.4, 0]);
  });
});

describe("speakerPose", () => {
  it("seat index 0 sits on the +Z axis as a 3/4 mid-shot", () => {
    const { pos, look } = speakerPose(0, 6); // angle 0 -> sin0=0, cos0=1, r=5
    expect(pos[0]).toBeCloseTo(0, 5);
    expect(pos[1]).toBeCloseTo(7.25, 5); // r*1.45
    expect(pos[2]).toBeCloseTo(6.25, 5); // sZ(=5)*1.25
    expect(look[0]).toBeCloseTo(0, 5);
    expect(look[1]).toBeCloseTo(0.6, 5);
    expect(look[2]).toBeCloseTo(2.5, 5); // sZ*0.5
  });
  it("places the opposite seat across the table", () => {
    const b = speakerPose(3, 6); // angle = pi -> cos(pi) = -1 -> sZ=-5
    expect(b.pos[2]).toBeCloseTo(-6.25, 5);
  });
});

describe("decideCamera", () => {
  const base = {
    count: 6,
    nowMs: 10_000,
    establishUntilMs: 0,
    recenterUntilMs: 0,
    reducedMotion: false,
  };

  it("lobby phase yields lobby mode (orbit handled by the component)", () => {
    const d = decideCamera({ ...base, phase: "START_SCREEN", speakerIndex: null });
    expect(d.mode).toBe("lobby");
  });

  it("follows the active speaker with a slow push-in when idle", () => {
    const d = decideCamera({ ...base, phase: "DAY_DEBATE", speakerIndex: 2 });
    expect(d.mode).toBe("follow");
    expect(d.posLambda).toBe(SLOW_LAMBDA);
    expect(d.pos).toEqual(speakerPose(2, 6).pos);
  });

  it("a phase-establish window forces a fast wide cut over any speaker", () => {
    const d = decideCamera({
      ...base,
      phase: "NIGHT_WOLF",
      speakerIndex: 2,
      establishUntilMs: 10_500,
    });
    expect(d.mode).toBe("wide");
    expect(d.posLambda).toBe(FAST_LAMBDA);
    expect(d.pos).toEqual(homePose(6).pos);
  });

  it("a post-speech recenter hold overrides a freshly-arrived next speaker", () => {
    const d = decideCamera({
      ...base,
      phase: "DAY_DEBATE",
      speakerIndex: 4,
      recenterUntilMs: 10_400,
    });
    expect(d.mode).toBe("wide");
    expect(d.posLambda).toBe(FAST_LAMBDA);
    expect(d.pos).toEqual(homePose(6).pos);
  });

  it("returns to a gentle wide overview when no one is speaking", () => {
    const d = decideCamera({ ...base, phase: "DAY_VOTE", speakerIndex: null });
    expect(d.mode).toBe("wide");
    expect(d.posLambda).toBe(SLOW_LAMBDA);
    expect(d.pos).toEqual(homePose(6).pos);
  });

  it("reduced motion never pushes in on a speaker", () => {
    const d = decideCamera({
      ...base,
      phase: "DAY_DEBATE",
      speakerIndex: 2,
      reducedMotion: true,
    });
    expect(d.mode).toBe("wide");
    expect(d.pos).toEqual(homePose(6).pos);
  });

  it("once both wide windows expire, follow resumes", () => {
    const d = decideCamera({
      ...base,
      phase: "DAY_DEBATE",
      speakerIndex: 1,
      nowMs: 20_000,
      establishUntilMs: 10_500,
      recenterUntilMs: 10_400,
    });
    expect(d.mode).toBe("follow");
  });
});

describe("RECENTER_HOLD_MS", () => {
  it("holds the wide beat long enough to read the board", () => {
    expect(RECENTER_HOLD_MS).toBeGreaterThanOrEqual(500);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run (from `frontend/`): `npm test -- src/lib/cameraDirector.test.ts`
Expected: FAIL — `Failed to resolve import "./cameraDirector"` / module not found.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/lib/cameraDirector.ts`:

```ts
import type { GameState } from "../types";

export type Vec3 = [number, number, number];

export interface CamPose {
  pos: Vec3;
  look: Vec3;
}

/** "lobby" = caller runs its own orbit; "wide" = home framing; "follow" = speaker shot. */
export type CamMode = "lobby" | "wide" | "follow";

export interface CamDecision {
  mode: CamMode;
  pos: Vec3;
  look: Vec3;
  posLambda: number;
  lookLambda: number;
}

export interface CamInput {
  phase: GameState["phase"] | undefined;
  /** Array index of the speaking seat within the players ring, or null. */
  speakerIndex: number | null;
  /** Number of seats around the table. */
  count: number;
  /** performance.now() at this frame. */
  nowMs: number;
  /** ts until which a phase-change establish shot holds wide (0 = none). */
  establishUntilMs: number;
  /** ts until which a post-speech recenter holds wide (0 = none). */
  recenterUntilMs: number;
  /** prefers-reduced-motion: when true, never push in on a speaker. */
  reducedMotion: boolean;
}

/** Duration of the forced wide "hold" after a speech ends (the cinematic beat). */
export const RECENTER_HOLD_MS = 700;

// Framing factors (multiplied by the table radius).
export const HOME_Y_FACTOR = 1.85;
export const HOME_Z_FACTOR = 2.6;
export const HOME_LOOK_Y = 0.4;
export const SPEAKER_XZ_FACTOR = 1.25;
export const SPEAKER_Y_FACTOR = 1.45;
export const SPEAKER_LOOK_FACTOR = 0.5;
export const SPEAKER_LOOK_Y = 0.6;

// Damping lambdas for THREE.MathUtils.damp (frame-rate independent; higher = snappier).
export const FAST_LAMBDA = 7.0; // decisive cut back to wide
export const SLOW_LAMBDA = 3.0; // unhurried push-in / gentle drift
export const FAST_LOOK_LAMBDA = 7.5;
export const SLOW_LOOK_LAMBDA = 3.5;

/** Seat-ring radius — mirrors the value SpeakerSeat/render use so the camera lines up. */
export function tableRadius(count: number): number {
  return Math.max(5, count * 0.72);
}

export function homePose(count: number): CamPose {
  const r = tableRadius(count);
  return { pos: [0, r * HOME_Y_FACTOR, r * HOME_Z_FACTOR], look: [0, HOME_LOOK_Y, 0] };
}

export function speakerPose(speakerIndex: number, count: number): CamPose {
  const total = Math.max(1, count);
  const angle = (speakerIndex / total) * Math.PI * 2;
  const r = tableRadius(count);
  const sX = Math.sin(angle) * r;
  const sZ = Math.cos(angle) * r;
  return {
    pos: [sX * SPEAKER_XZ_FACTOR, r * SPEAKER_Y_FACTOR, sZ * SPEAKER_XZ_FACTOR],
    look: [sX * SPEAKER_LOOK_FACTOR, SPEAKER_LOOK_Y, sZ * SPEAKER_LOOK_FACTOR],
  };
}

export function decideCamera(input: CamInput): CamDecision {
  const {
    phase,
    speakerIndex,
    count,
    nowMs,
    establishUntilMs,
    recenterUntilMs,
    reducedMotion,
  } = input;

  const home = homePose(count);

  // Lobby keeps its bespoke time-based orbit in the component; pose here is a fallback.
  if (phase === "START_SCREEN") {
    return {
      mode: "lobby",
      pos: home.pos,
      look: home.look,
      posLambda: SLOW_LAMBDA,
      lookLambda: SLOW_LOOK_LAMBDA,
    };
  }

  // Forced wide window: a phase-change establish beat OR a post-speech hold.
  // Fast, decisive cut — and it deliberately overrides a freshly-set next speaker.
  if (nowMs < establishUntilMs || nowMs < recenterUntilMs) {
    return {
      mode: "wide",
      pos: home.pos,
      look: home.look,
      posLambda: FAST_LAMBDA,
      lookLambda: FAST_LOOK_LAMBDA,
    };
  }

  // Follow the active speaker with an unhurried push-in (unless reduced motion).
  if (speakerIndex != null && !reducedMotion) {
    const sp = speakerPose(speakerIndex, count);
    return {
      mode: "follow",
      pos: sp.pos,
      look: sp.look,
      posLambda: SLOW_LAMBDA,
      lookLambda: SLOW_LOOK_LAMBDA,
    };
  }

  // No speaker (between turns, voting, sheriff phases) → gentle wide home.
  return {
    mode: "wide",
    pos: home.pos,
    look: home.look,
    posLambda: SLOW_LAMBDA,
    lookLambda: SLOW_LOOK_LAMBDA,
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run (from `frontend/`): `npm test -- src/lib/cameraDirector.test.ts`
Expected: PASS — all ~10 tests green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/cameraDirector.ts frontend/src/lib/cameraDirector.test.ts
git commit -m "feat(fe): pure cameraDirector (home/speaker poses + decision machine)"
```

---

## Task 2: Wire CameraTracker to the director

**Files:**
- Modify: `frontend/src/components/ThreeCanvas.tsx` (imports at top; `CameraTracker` body lines ~78–190; `targetCamPos` seed; `<Canvas camera>` prop ~line 813)

- [ ] **Step 1: Add imports**

In `frontend/src/components/ThreeCanvas.tsx`, the current import block is:

```tsx
import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import { useGameStore } from "../store";
import { ESTABLISH_MS } from "../lib/phaseStage";
```

Replace it with (adds `useReducedMotion`, the director, and the `GameState` type; keeps `ESTABLISH_MS`):

```tsx
import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import { useReducedMotion } from "motion/react";
import { useGameStore } from "../store";
import { ESTABLISH_MS } from "../lib/phaseStage";
import { decideCamera, RECENTER_HOLD_MS } from "../lib/cameraDirector";
import type { GameState } from "../types";
```

- [ ] **Step 2: Replace the whole `CameraTracker` function**

Replace the entire existing `CameraTracker` function (from `function CameraTracker() {` through its closing `}` and `return null;`, currently lines ~78–190) with:

```tsx
function CameraTracker() {
  const { camera } = useThree();
  const gameState = useGameStore((state) => state.state);
  const setupCount = useGameStore((state) => state.setupCount);
  const currentSpeakerId = gameState?.currentSpeakerId ?? null;
  const players = gameState?.players || [];
  const phase = gameState?.phase;
  const reducedMotion = useReducedMotion() ?? false;

  // Damp targets (seeded at the unified home framing for a 6-seat table).
  const targetCamPos = useRef(new THREE.Vector3(0, 9.25, 13));
  const targetLookAt = useRef(new THREE.Vector3(0, 0.4, 0));
  const currentLookAt = useRef(new THREE.Vector3(0, 0.4, 0));

  // "Wide window" timers (performance.now() deadlines; 0 = inactive).
  const establishUntilRef = useRef<number>(0);
  const recenterUntilRef = useRef<number>(0);
  const prevPhaseRef = useRef<GameState["phase"] | undefined>(phase);
  const prevSpeakerRef = useRef<number | null>(currentSpeakerId);

  // Any in-game phase change (coarse day/night OR a sub-phase like vote/sheriff/
  // night-skill) opens a wide "establish" beat. Lobby is excluded (it orbits).
  useEffect(() => {
    const prev = prevPhaseRef.current;
    if (phase && phase !== prev && phase !== "START_SCREEN") {
      establishUntilRef.current = performance.now() + ESTABLISH_MS;
    }
    prevPhaseRef.current = phase;
  }, [phase]);

  // A speech ending (speaker moving away from a previous speaker) opens a wide
  // "hold" beat that deliberately survives into the next speaker's first moments.
  useEffect(() => {
    const prev = prevSpeakerRef.current;
    if (prev != null && currentSpeakerId !== prev) {
      recenterUntilRef.current = performance.now() + RECENTER_HOLD_MS;
    }
    prevSpeakerRef.current = currentSpeakerId;
  }, [currentSpeakerId]);

  useFrame((state, delta) => {
    // Lobby keeps its bespoke slow-orbit framing, untouched.
    if (phase === "START_SCREEN") {
      const time = state.clock.getElapsedTime();
      const orbitSpeed = 0.08;
      const pCount = setupCount !== null ? setupCount : (players.length || 6);
      const radius = Math.max(5, pCount * 0.72);
      const orbitRadius = radius * 3.4; // majestic outer distance

      const x = Math.sin(time * orbitSpeed) * orbitRadius;
      const z = Math.cos(time * orbitSpeed) * orbitRadius;
      targetCamPos.current.set(x, radius * 1.6, z);

      // Offset the look target so the round table sits to the screen's right.
      const dirVec = new THREE.Vector3()
        .subVectors(new THREE.Vector3(0, 0.4, 0), targetCamPos.current)
        .normalize();
      const upVec = new THREE.Vector3(0, 1, 0);
      const rightVec = new THREE.Vector3().crossVectors(dirVec, upVec).normalize();
      let offsetScale = 0;
      if (typeof window !== "undefined" && window.innerWidth > window.innerHeight) {
        offsetScale = radius * 0.8;
      }
      const lookTarget = new THREE.Vector3(0, 0.4, 0).add(rightVec.multiplyScalar(-offsetScale));
      targetLookAt.current.copy(lookTarget);

      camera.position.x = THREE.MathUtils.damp(camera.position.x, targetCamPos.current.x, 3.5, delta);
      camera.position.y = THREE.MathUtils.damp(camera.position.y, targetCamPos.current.y, 3.5, delta);
      camera.position.z = THREE.MathUtils.damp(camera.position.z, targetCamPos.current.z, 3.5, delta);
      currentLookAt.current.x = THREE.MathUtils.damp(currentLookAt.current.x, targetLookAt.current.x, 4.0, delta);
      currentLookAt.current.y = THREE.MathUtils.damp(currentLookAt.current.y, targetLookAt.current.y, 4.0, delta);
      currentLookAt.current.z = THREE.MathUtils.damp(currentLookAt.current.z, targetLookAt.current.z, 4.0, delta);
      camera.lookAt(currentLookAt.current);
      return;
    }

    const count = players.length > 0 ? players.length : (setupCount ?? 6);
    const speakerIndex =
      currentSpeakerId != null ? players.findIndex((p) => p.id === currentSpeakerId) : -1;

    const decision = decideCamera({
      phase,
      speakerIndex: speakerIndex >= 0 ? speakerIndex : null,
      count,
      nowMs: performance.now(),
      establishUntilMs: establishUntilRef.current,
      recenterUntilMs: recenterUntilRef.current,
      reducedMotion,
    });

    targetCamPos.current.set(decision.pos[0], decision.pos[1], decision.pos[2]);
    targetLookAt.current.set(decision.look[0], decision.look[1], decision.look[2]);

    camera.position.x = THREE.MathUtils.damp(camera.position.x, targetCamPos.current.x, decision.posLambda, delta);
    camera.position.y = THREE.MathUtils.damp(camera.position.y, targetCamPos.current.y, decision.posLambda, delta);
    camera.position.z = THREE.MathUtils.damp(camera.position.z, targetCamPos.current.z, decision.posLambda, delta);

    currentLookAt.current.x = THREE.MathUtils.damp(currentLookAt.current.x, targetLookAt.current.x, decision.lookLambda, delta);
    currentLookAt.current.y = THREE.MathUtils.damp(currentLookAt.current.y, targetLookAt.current.y, decision.lookLambda, delta);
    currentLookAt.current.z = THREE.MathUtils.damp(currentLookAt.current.z, targetLookAt.current.z, decision.lookLambda, delta);
    camera.lookAt(currentLookAt.current);
  });

  return null;
}
```

- [ ] **Step 3: Bump the initial `<Canvas>` camera to the unified home**

Find (currently ~line 813):

```tsx
        camera={{ position: [0, 8.5, 12.0], fov: 45 }}
```

Replace with:

```tsx
        camera={{ position: [0, 9.25, 13], fov: 45 }}
```

- [ ] **Step 4: Typecheck**

Run (from `frontend/`): `npm run lint`
Expected: PASS — `tsc --noEmit` reports no errors. (If it flags an unused `ESTABLISH_MS`, that means Step 2's phase `useEffect` was dropped — re-add it.)

- [ ] **Step 5: Run the full test suite**

Run (from `frontend/`): `npm test`
Expected: PASS — the new `cameraDirector` tests plus all pre-existing suites (including `phaseStage`, `roles`) stay green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ThreeCanvas.tsx
git commit -m "feat(fe): camera re-centers to home on speech-end + every phase change"
```

---

## Task 3: Real-machine verification (live game)

`CameraTracker` is imperative R3F code that unit tests can't exercise, so verify the integrated behavior in a browser. No API key is required — use the keyless demo run path established previously (`model: demo`).

**Files:** none (verification only)

- [ ] **Step 1: Start a keyless demo run + the dev server**

From the repo root, generate/serve a demo run and start Vite bound to IPv4 (Vite may otherwise bind IPv6-only, which Chrome-over-localhost refuses):

```bash
cd frontend && npm run dev -- --host 127.0.0.1 --port 5180
```

Obtain a spectatable `run_id` (reuse the prior `demo-6.yaml` keyless CLI demo, or any in-progress run) and open `http://127.0.0.1:5180/game?run_id=<RUN_ID>&view=god` via Chrome DevTools MCP (`new_page`).

- [ ] **Step 2: Verify the speech-end wide beat**

Watch two consecutive day-discussion speakers. Confirm the rhythm: moderate 3/4 framing on speaker A → **fast cut back to a wide shot showing all seats** when A finishes → wide hold (~0.7s, persists even as B's halo/spotlight lights up) → **slow push-in** to B. Take a `take_screenshot` mid-hold to confirm all 6 pieces are in frame.

Expected: every turn boundary shows the whole board; the camera is never face-locked across a hand-off.

- [ ] **Step 3: Verify the phase-change establish beat**

Watch a night→day (or day→night) boundary and a sub-phase boundary (e.g. entering `DAY_VOTE` or `DAY_SHERIFF_RUN`). Confirm the camera pulls back to the same wide home framing as the boundary lands, independent of any active speaker.

Expected: each phase/sub-phase entry briefly re-establishes the wide board.

- [ ] **Step 4: Verify lobby is untouched**

Open `http://127.0.0.1:5180/` (setup screen, `START_SCREEN`). Confirm the slow majestic orbit with the table offset to the right still plays exactly as before.

Expected: no regression to the lobby camera.

- [ ] **Step 5: (Optional) Verify reduced-motion**

In Chrome DevTools, emulate `prefers-reduced-motion: reduce` (`emulate` / rendering emulation), reload a live run, and confirm the camera stays at the wide home framing and does not push in on speakers.

Expected: no speaker push-ins under reduced motion; board stays fully visible.

- [ ] **Step 6: Tear down**

Stop the dev server and close the demo run. No code committed in this task.

---

## Self-Review

**1. Spec coverage:**
- Model A (focus → fast wide hold → slow push-in): `decideCamera` precedence (wide window beats `follow`) + `FAST_LAMBDA`/`SLOW_LAMBDA` (Task 1); `recenterUntilRef` latch on speech-end (Task 2). ✓
- Unified home framing for hold + establish + initial: `homePose` (Task 1); `<Canvas camera>` + ref seed (Task 2 Steps 2–3). ✓
- Softened 3/4 speaker shot: `speakerPose` (Task 1). ✓
- Triggers (speech-end + any phase change incl. sub-phases): two `useEffect`s (Task 2 Step 2). ✓
- Motion feel (fast/slow split): lambda constants (Task 1). ✓
- Reduced motion: flag in `decideCamera` + `useReducedMotion` (Tasks 1–2). ✓
- Live-only scope: inherent (Replay never mounts `ThreeCanvas`). ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows full code; every command has an expected result. ✓

**3. Type consistency:** `decideCamera`/`CamInput`/`CamDecision`/`CamPose`/`Vec3`, `homePose`, `speakerPose`, `tableRadius`, `RECENTER_HOLD_MS`, `FAST_LAMBDA`, `SLOW_LAMBDA` are defined in Task 1 and consumed with identical names/signatures in Tasks 1–2. `CamInput.phase` is `GameState["phase"] | undefined`, matching `gameState?.phase` passed from the component. The component imports exactly `decideCamera` and `RECENTER_HOLD_MS` (plus the retained `ESTABLISH_MS` from `phaseStage`). ✓

---

## Notes for the Executor

- **Concurrency hazard (documented in memory):** this repo is worked by multiple concurrent agents sharing one working dir; branches/checkouts can mutate mid-task. Do all edit/verify/commit work in a **dedicated git worktree** off your own feature branch — not the shared checkout. Each worktree needs its own `npm install` (node_modules isn't shared). Pass `--host 127.0.0.1` to Vite.
- The coarse-stage card/flash (`stageFx`, `PhaseTransitionCard`, `PhaseBadge`) is intentionally untouched — the camera is now driven purely off `gameState.phase` + speaker transitions, decoupled from `stageFx`.
- Tuning constants (`RECENTER_HOLD_MS`, lambdas, framing factors) live in one place (`cameraDirector.ts`) so real-machine tuning in Task 3 is a single-file edit.
