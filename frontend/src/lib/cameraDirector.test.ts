import { describe, it, expect } from "vitest";
import {
  tableRadius,
  homePose,
  speakerPose,
  decideCamera,
  RECENTER_HOLD_MS,
  WIDE_LAMBDA,
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
    expect(d.posLambda).toBe(WIDE_LAMBDA);
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
    expect(d.posLambda).toBe(WIDE_LAMBDA);
    expect(d.pos).toEqual(homePose(6).pos);
  });

  it("the wide pull-back eases rather than snapping (gentler than the old fast cut)", () => {
    expect(WIDE_LAMBDA).toBeLessThan(5);
    expect(WIDE_LAMBDA).toBeGreaterThan(SLOW_LAMBDA);
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
