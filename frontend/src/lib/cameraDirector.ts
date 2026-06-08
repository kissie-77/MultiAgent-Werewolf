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
