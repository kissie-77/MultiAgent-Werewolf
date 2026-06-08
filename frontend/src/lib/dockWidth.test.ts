import { describe, it, expect } from "vitest";
import { clampDockWidth, DOCK_MIN_WIDTH, DOCK_MAX_WIDTH } from "./dockWidth";

describe("clampDockWidth", () => {
  it("clamps below the minimum up to 300", () => {
    expect(clampDockWidth(120, 1600)).toBe(DOCK_MIN_WIDTH);
    expect(clampDockWidth(DOCK_MIN_WIDTH, 1600)).toBe(300);
  });
  it("caps at min(720, 90% viewport)", () => {
    expect(clampDockWidth(9999, 1600)).toBe(DOCK_MAX_WIDTH); // 720 < 1440
    expect(clampDockWidth(9999, 600)).toBe(540); // floor(600*0.9)=540 < 720
  });
  it("passes mid-range values through (rounded)", () => {
    expect(clampDockWidth(480.4, 1600)).toBe(480);
    expect(clampDockWidth(512.6, 1600)).toBe(513);
  });
  it("never goes below 300 even on a very narrow viewport", () => {
    // floor(320*0.9)=288 < 300 → floor still returns the 300 lower bound
    expect(clampDockWidth(288, 320)).toBe(300);
    expect(clampDockWidth(9999, 320)).toBe(300);
  });
});
