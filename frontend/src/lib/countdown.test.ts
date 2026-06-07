import { describe, it, expect } from "vitest";
import { remainingSeconds } from "./countdown";

describe("remainingSeconds", () => {
  it("returns the full deadline at the start", () => {
    expect(remainingSeconds(120, 1000, 1000)).toBe(120);
  });

  it("counts down as time elapses", () => {
    expect(remainingSeconds(120, 0, 30_000)).toBe(90);
  });

  it("clamps to zero once the deadline passes", () => {
    expect(remainingSeconds(45, 0, 60_000)).toBe(0);
  });

  it("returns zero for a missing or non-positive deadline", () => {
    expect(remainingSeconds(0, 0, 0)).toBe(0);
    expect(remainingSeconds(-5, 0, 0)).toBe(0);
  });

  it("returns zero for a non-finite deadline", () => {
    expect(remainingSeconds(Number.NaN, 0, 0)).toBe(0);
  });
});
