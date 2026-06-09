import { describe, it, expect } from "vitest";
import { resolveSceneMode, sceneTheme, sceneIsNight } from "./sceneTheme";

describe("sceneIsNight (phase-driven night, matches header)", () => {
  it("is night for every NIGHT_* phase", () => {
    expect(sceneIsNight("NIGHT_WOLF")).toBe(true);
    expect(sceneIsNight("NIGHT_SEER")).toBe(true);
    expect(sceneIsNight("NIGHT_WITCH")).toBe(true);
  });

  it("is NOT night for any day phase (the bug: day-1 must not read as night)", () => {
    expect(sceneIsNight("DAY_SHERIFF_RUN")).toBe(false);
    expect(sceneIsNight("DAY_SHERIFF_VOTE")).toBe(false);
    expect(sceneIsNight("DAY_ANNOUNCEMENT")).toBe(false);
    expect(sceneIsNight("DAY_DEBATE")).toBe(false);
    expect(sceneIsNight("DAY_VOTE")).toBe(false);
  });

  it("is NOT night for lobby / role-choice / game-over", () => {
    expect(sceneIsNight("START_SCREEN")).toBe(false);
    expect(sceneIsNight("ROLE_CHOICE")).toBe(false);
    expect(sceneIsNight("GAME_OVER")).toBe(false);
  });

  it("is NOT night for undefined / empty phase", () => {
    expect(sceneIsNight(undefined)).toBe(false);
    expect(sceneIsNight("")).toBe(false);
  });
});

describe("resolveSceneMode", () => {
  it("murder alert beats night beats day", () => {
    expect(resolveSceneMode(true, true)).toBe("murder");
    expect(resolveSceneMode(false, true)).toBe("murder");
    expect(resolveSceneMode(true, false)).toBe("night");
    expect(resolveSceneMode(false, false)).toBe("day");
  });
});

describe("sceneTheme", () => {
  it("day is markedly brighter than the old 0.38 ambient", () => {
    expect(sceneTheme("day").ambientIntensity).toBeGreaterThan(1.0);
  });

  it("night is readable but dim (between the old 0.15 and day)", () => {
    const night = sceneTheme("night").ambientIntensity;
    expect(night).toBeGreaterThan(0.3);
    expect(night).toBeLessThan(sceneTheme("day").ambientIntensity);
  });

  it("day key light is warm/strong, night key light is cooler/weaker", () => {
    expect(sceneTheme("day").dirIntensity).toBeGreaterThan(sceneTheme("night").dirIntensity);
  });

  it("day and night backgrounds are distinct", () => {
    expect(sceneTheme("day").bg).not.toBe(sceneTheme("night").bg);
  });

  it("murder alert is red", () => {
    expect(sceneTheme("murder").ambientColor).toBe("#ff1100");
  });

  it("every theme exposes accent + accentSoft + a 3-tuple light position", () => {
    for (const mode of ["day", "night", "murder"] as const) {
      const t = sceneTheme(mode);
      expect(typeof t.accent).toBe("string");
      expect(typeof t.accentSoft).toBe("string");
      expect(t.dirPos).toHaveLength(3);
    }
  });
});
