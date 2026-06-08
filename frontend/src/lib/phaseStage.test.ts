import { describe, it, expect } from "vitest";
import {
  coarseStage,
  shouldShowCard,
  stageCardText,
  stageBadge,
  MIN_GAP_MS,
} from "./phaseStage";

describe("coarseStage", () => {
  it("maps fine phases to coarse buckets", () => {
    expect(coarseStage("START_SCREEN")).toBe("lobby");
    expect(coarseStage("ROLE_CHOICE")).toBe("lobby");
    expect(coarseStage("NIGHT_WOLF")).toBe("night");
    expect(coarseStage("NIGHT_SEER")).toBe("night");
    expect(coarseStage("NIGHT_WITCH")).toBe("night");
    expect(coarseStage("DAY_SHERIFF_RUN")).toBe("day");
    expect(coarseStage("DAY_ANNOUNCEMENT")).toBe("day");
    expect(coarseStage("DAY_DEBATE")).toBe("day");
    expect(coarseStage("DAY_VOTE")).toBe("day");
    expect(coarseStage("GAME_OVER")).toBe("over");
  });
});

describe("shouldShowCard", () => {
  it("fires only for night/day, on real change, after the burst gap", () => {
    expect(shouldShowCard("lobby", "night", 5000, MIN_GAP_MS)).toBe(true);
    expect(shouldShowCard("night", "day", 5000, MIN_GAP_MS)).toBe(true);
    expect(shouldShowCard("day", "night", 5000, MIN_GAP_MS)).toBe(true);
  });
  it("suppresses same-stage, lobby/over targets, and replay bursts", () => {
    expect(shouldShowCard("night", "night", 5000, MIN_GAP_MS)).toBe(false);
    expect(shouldShowCard("night", "lobby", 5000, MIN_GAP_MS)).toBe(false);
    expect(shouldShowCard("day", "over", 5000, MIN_GAP_MS)).toBe(false);
    expect(shouldShowCard("day", "night", 40, MIN_GAP_MS)).toBe(false);
  });
});

describe("stageCardText", () => {
  it("nightfall card", () => {
    expect(stageCardText("night", 2, null)).toEqual({
      kicker: "夜幕降临",
      title: "第 2 夜",
      sub: "屏息",
      death: false,
      victimSeat: null,
    });
  });
  it("peaceful daybreak card", () => {
    expect(stageCardText("day", 3, null)).toEqual({
      kicker: "曙光破晓",
      title: "第 3 日",
      sub: "黎明",
      death: false,
      victimSeat: null,
    });
  });
  it("daybreak merged with death", () => {
    expect(stageCardText("day", 3, 5)).toEqual({
      kicker: "曙光破晓",
      title: "第 3 日",
      sub: "5 号遇害",
      death: true,
      victimSeat: 5,
    });
  });
  it("returns null for non-card stages", () => {
    expect(stageCardText("lobby", 1, null)).toBeNull();
    expect(stageCardText("over", 1, null)).toBeNull();
  });
});

describe("stageBadge", () => {
  it("night badge", () => {
    expect(stageBadge("NIGHT_WOLF", 1)).toEqual({
      icon: "moon",
      dayText: "第 1 夜",
      phaseText: "狼人潜行屠杀",
    });
  });
  it("day badge falls back to a generic label", () => {
    expect(stageBadge("DAY_DEBATE", 2)).toEqual({
      icon: "sun",
      dayText: "第 2 日",
      phaseText: "圆形议事辩驳",
    });
  });
  it("lobby badge", () => {
    expect(stageBadge("START_SCREEN", 0)).toEqual({
      icon: "wait",
      dayText: "候场集结",
      phaseText: "等待入场",
    });
  });
});
