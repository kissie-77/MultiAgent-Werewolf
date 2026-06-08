import { describe, it, expect } from "vitest";
import {
  GOD_ROLES,
  topRoleOf,
  selectGodRoleRows,
  selectWolfMatrices,
  type WolfCampMindV2,
  type GodRoleBeliefV2,
} from "./godRoleIntel";
import type { InsightPlayer } from "./insightMap";

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

function ip(seat: number, camp: string, alive = true, role = "Villager"): InsightPlayer {
  return { seat, id: `player_${seat}`, name: `P${seat}`, role, camp, alive };
}

describe("selectWolfMatrices", () => {
  // P1女巫 P2预言家 P3狼 P4狼 P5村 P6村
  const players: InsightPlayer[] = [
    ip(1, "good", true, "Witch"),
    ip(2, "good", true, "Seer"),
    ip(3, "werewolf", true, "Werewolf"),
    ip(4, "werewolf", true, "Werewolf"),
    ip(5, "good", true, "Villager"),
    ip(6, "good", true, "Villager"),
  ];

  it("returns [] when no living wolves", () => {
    const noWolves = players.map((p) => (p.camp === "werewolf" ? { ...p, alive: false } : p));
    expect(selectWolfMatrices(noWolves, null, 1)).toEqual([]);
  });

  it("builds one matrix per living wolf, with an all-zero skeleton over living non-wolf targets", () => {
    const out = selectWolfMatrices(players, null, 2);
    expect(out.map((m) => m.owner_seat)).toEqual([3, 4]);
    const m3 = out[0];
    expect(Object.keys(m3.god_role_intel).sort()).toEqual(["1", "2", "5", "6"]);
    const t2 = m3.god_role_intel["2"];
    expect(t2.threat_score).toBe(0);
    expect(t2.priority).toBe("low");
    expect(t2.role_distribution).toEqual({ Seer: 0, Witch: 0, Guard: 0, Hunter: 0, Villager: 0 });
    expect(t2.updated_round).toBe(2);
  });

  it("overlays real god_role_intel onto the skeleton, keeping un-predicted targets at 0", () => {
    const minds = {
      3: {
        schema: "wolf_camp_mind_v2" as const,
        owner_seat: 3,
        round: 3,
        contributor_seat: 3,
        god_role_intel: {
          "2": {
            target_seat: 2,
            role_distribution: { Seer: 0.9, Witch: 0.05, Guard: 0.02, Hunter: 0, Villager: 0.03 },
            threat_score: 0.92,
            priority: "kill_tonight" as const,
            evidence: ["2号跳预言家"],
            updated_round: 2,
            contributors: [3],
          },
        },
        exposure_radar: {},
      },
    };
    const out = selectWolfMatrices(players, minds, 2);
    const m3 = out.find((m) => m.owner_seat === 3)!;
    expect(m3.god_role_intel["2"].threat_score).toBeCloseTo(0.92);
    expect(m3.god_role_intel["2"].priority).toBe("kill_tonight");
    expect(m3.god_role_intel["5"].threat_score).toBe(0);
    expect(m3.round).toBe(3); // 有真实快照 → 用其自带轮次（3），而非传入的 2
    const m4 = out.find((m) => m.owner_seat === 4)!;
    expect(m4.god_role_intel["2"].threat_score).toBe(0);
    expect(m4.round).toBe(2); // 纯骨架 → 回退到传入轮次
  });

  it("drops dead non-wolf targets from the skeleton", () => {
    const p = players.map((x) => (x.seat === 6 ? { ...x, alive: false } : x));
    const out = selectWolfMatrices(p, null, 1);
    expect(Object.keys(out[0].god_role_intel).sort()).toEqual(["1", "2", "5"]);
  });
});
