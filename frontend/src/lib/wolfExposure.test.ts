import { describe, it, expect } from "vitest";
import { stanceFromExposure, selectWolfExposure } from "./wolfExposure";
import type { BeliefSnapshot } from "../api/insightTypes";
import type { InsightPlayer } from "./insightMap";

function player(seat: number, camp: string, alive = true, role = "Werewolf"): InsightPlayer {
  return { seat, id: `player_${seat}`, name: `P${seat}`, role, camp, alive };
}

// 一条观察者快照：observer 对每个 target 的狼概率由 probs[target_seat] 给出
function snap(observerSeat: number, probs: Record<number, number>): BeliefSnapshot {
  return {
    round: 1,
    phase: "day_discussion",
    anchor: "after_speech",
    observer_id: `player_${observerSeat}`,
    observer_seat: observerSeat,
    vote_intention: { seat: 0, reason: "" },
    first_order: Object.entries(probs).map(([t, p]) => ({
      target_seat: Number(t),
      wolf_probability: p,
      reason: null,
      note: null,
    })),
  };
}

describe("stanceFromExposure", () => {
  it("maps exposure to stance buckets at backend thresholds", () => {
    expect(stanceFromExposure(0)).toBe("push");
    expect(stanceFromExposure(0.24)).toBe("push");
    expect(stanceFromExposure(0.25)).toBe("hide");
    expect(stanceFromExposure(0.45)).toBe("counter");
    expect(stanceFromExposure(0.6)).toBe("bus");
    expect(stanceFromExposure(0.85)).toBe("sacrifice");
    expect(stanceFromExposure(1)).toBe("sacrifice");
  });
});

describe("selectWolfExposure", () => {
  // 4 玩家：P1 狼、P2 狼(队友)、P3 村、P4 村
  const players = [
    player(1, "werewolf"),
    player(2, "werewolf"),
    player(3, "villager"),
    player(4, "villager"),
  ];

  it("exposure = max of non-wolf observers' wolf_probability toward the wolf", () => {
    // 对 P1 的狼概率：P2(队友,排除)=1.0, P3=0.3, P4=0.7 → max(非狼)=0.7
    const beliefs = [snap(2, { 1: 1.0 }), snap(3, { 1: 0.3 }), snap(4, { 1: 0.7 })];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.exposure).toBeCloseTo(0.7);
    expect(p1.stance).toBe("bus"); // 0.7 → ≥0.6
  });

  it("excludes fellow wolves and the wolf itself from the column", () => {
    // 仅队友 P2 给 P1 标 1.0，无村民数据 → 非狼列为空 → exposure 0
    const beliefs = [snap(2, { 1: 1.0 }), snap(1, { 1: 0 })];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.exposure).toBe(0);
    expect(p1.topSuspectors).toEqual([]);
    expect(p1.stance).toBe("push");
  });

  it("topSuspectors: co-leaders within 0.15 of the top, capped at 2", () => {
    // P1: P3=0.62, P4=0.50 (相差0.12≤0.15→并列)
    const beliefs = [snap(3, { 1: 0.62 }), snap(4, { 1: 0.5 })];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.exposure).toBeCloseTo(0.62);
    expect(p1.topSuspectors.map((s) => s.seat)).toEqual([3, 4]);
  });

  it("topSuspectors: drops the second when gap > 0.15", () => {
    const beliefs = [snap(3, { 1: 0.62 }), snap(4, { 1: 0.4 })];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.topSuspectors.map((s) => s.seat)).toEqual([3]);
  });

  it("rows sorted by exposure desc, alive wolves only", () => {
    // P1 狼 exposure 0.3，P2 狼 exposure 0.8 → 期望顺序 [2,1]
    const beliefs = [snap(3, { 1: 0.3, 2: 0.8 }), snap(4, { 1: 0.2, 2: 0.1 })];
    const rows = selectWolfExposure(beliefs, players);
    expect(rows.map((r) => r.wolfSeat)).toEqual([2, 1]);
  });

  it("returns [] when no living wolves or beliefs missing", () => {
    const deadWolves = [player(1, "werewolf", false), player(3, "villager")];
    expect(selectWolfExposure([snap(3, { 1: 0.9 })], deadWolves)).toEqual([]);
    expect(selectWolfExposure(null, players)).toEqual([]);
    expect(selectWolfExposure([], players)).toEqual([]);
  });
});
