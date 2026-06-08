import { describe, it, expect } from "vitest";
import {
  GOD_ROLES,
  topRoleOf,
  selectGodRoleRows,
  type WolfCampMindV2,
  type GodRoleBeliefV2,
} from "./godRoleIntel";

function belief(
  target_seat: number,
  dist: Partial<Record<string, number>>,
  threat: number,
  priority: GodRoleBeliefV2["priority"] = "low",
): GodRoleBeliefV2 {
  return {
    target_seat,
    role_distribution: dist as Record<string, number>,
    threat_score: threat,
    priority,
    evidence: [],
    updated_round: 1,
    contributors: [3],
  };
}

function record(intel: Record<string, GodRoleBeliefV2>): WolfCampMindV2 {
  return {
    schema: "wolf_camp_mind_v2",
    owner_seat: 3,
    round: 1,
    contributor_seat: 3,
    god_role_intel: intel,
    exposure_radar: {},
  };
}

describe("topRoleOf", () => {
  it("picks the argmax role", () => {
    expect(topRoleOf({ Seer: 0.1, Witch: 0.7, Guard: 0.2 })).toEqual({ role: "Witch", prob: 0.7 });
  });

  it("breaks ties by GOD_ROLES order (Seer first)", () => {
    // Seer 与 Witch 同为 0.4 → 取顺序在前的 Seer
    expect(topRoleOf({ Seer: 0.4, Witch: 0.4, Villager: 0.2 }).role).toBe("Seer");
  });

  it("treats missing roles as 0 and never returns negative prob", () => {
    expect(topRoleOf({})).toEqual({ role: "Seer", prob: 0 });
    expect(topRoleOf(null)).toEqual({ role: "Seer", prob: 0 });
  });
});

describe("selectGodRoleRows", () => {
  it("returns [] for null / missing intel", () => {
    expect(selectGodRoleRows(null)).toEqual([]);
    expect(selectGodRoleRows(undefined)).toEqual([]);
    expect(selectGodRoleRows({ god_role_intel: undefined } as unknown as WolfCampMindV2)).toEqual([]);
  });

  it("sorts rows by threat desc, then target seat asc", () => {
    const rows = selectGodRoleRows(
      record({
        "5": belief(5, { Villager: 0.8 }, 0.15),
        "2": belief(2, { Seer: 0.9 }, 0.92, "kill_tonight"),
        "1": belief(1, { Witch: 0.6 }, 0.92, "watch"), // 同威胁 0.92 → 座位升序 1 在 2 前
      }),
    );
    expect(rows.map((r) => r.targetSeat)).toEqual([1, 2, 5]);
    expect(rows[1].priority).toBe("kill_tonight");
  });

  it("fills all 5 god-role buckets even when backend omits some", () => {
    const rows = selectGodRoleRows(record({ "2": belief(2, { Seer: 0.75 }, 0.9) }));
    expect(Object.keys(rows[0].distribution).sort()).toEqual([...GOD_ROLES].sort());
    expect(rows[0].distribution.Hunter).toBe(0);
    expect(rows[0].topRole).toBe("Seer");
    expect(rows[0].topProb).toBeCloseTo(0.75);
  });
});
