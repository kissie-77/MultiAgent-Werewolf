/**
 * ③ 狼·神职猜测矩阵 — 纯派生逻辑。
 *
 * 消费后端 `wolf_camp_mind.jsonl` 的 `wolf_camp_mind_v2` 行（每只狼一份私有面板）。
 * 与后端 `strategy/wolf/camp_mind.py` 的 `GodRoleBelief` / `WolfExposureProfile` 对齐。
 * 阈值/角色集合镜像后端常量，后端若改需同步（脆性，见 spec）。
 */

/** 后端 _GOD_ROLES：role_distribution 的固定 5 档。顺序即并列时的优先序。 */
export const GOD_ROLES = ["Seer", "Witch", "Guard", "Hunter", "Villager"] as const;
export type GodRole = (typeof GOD_ROLES)[number];

export type GodRolePriority = "kill_tonight" | "watch" | "low";
export type WolfStanceV2 = "sacrifice" | "bus" | "counter" | "hide" | "push";

/** 角色中文名（神职矩阵列头用）。 */
export const GOD_ROLE_ZH: Record<GodRole, string> = {
  Seer: "预言家",
  Witch: "女巫",
  Guard: "守卫",
  Hunter: "猎人",
  Villager: "平民",
};

/** 处置优先级文案（狼视角）。 */
export const PRIORITY_LABEL: Record<GodRolePriority, string> = {
  kill_tonight: "🔪 今夜刀",
  watch: "👀 盯防",
  low: "💤 低危",
};

export interface GodRoleBeliefV2 {
  target_seat: number;
  role_distribution: Record<string, number>;
  threat_score: number;
  priority: GodRolePriority;
  evidence: string[];
  updated_round: number;
  contributors: number[];
}

export interface WolfExposureProfileV2 {
  wolf_seat: number;
  overall_exposure: number;
  cells: Record<string, number>;
  suggested_stance: WolfStanceV2;
  top_suspectors: { seat: number; suspicion: number }[];
}

/** 后端 wolf_camp_mind.jsonl 每行（wolf_camp_mind_v2 schema）。 */
export interface WolfCampMindV2 {
  schema: "wolf_camp_mind_v2";
  owner_seat: number;
  round: number;
  contributor_seat: number;
  god_role_intel: Record<string, GodRoleBeliefV2>;
  exposure_radar: Record<string, WolfExposureProfileV2>;
}

/** 一行已派生的神职猜测（供组件直接渲染）。 */
export interface GodRoleRow {
  targetSeat: number;
  /** 补全 5 档的概率分布（缺档补 0）。 */
  distribution: Record<GodRole, number>;
  /** 概率最高的角色（并列取 GOD_ROLES 顺序中的首个）。 */
  topRole: GodRole;
  topProb: number;
  threat: number;
  priority: GodRolePriority;
  evidence: string[];
}

/** 取分布中概率最高的神职；并列时按 GOD_ROLES 顺序取首个（确定性）。 */
export function topRoleOf(dist: Record<string, number> | null | undefined): {
  role: GodRole;
  prob: number;
} {
  let best: GodRole = GOD_ROLES[0];
  let bestProb = -1;
  for (const role of GOD_ROLES) {
    const p = Number(dist?.[role] ?? 0);
    if (p > bestProb) {
      bestProb = p;
      best = role;
    }
  }
  return { role: best, prob: Math.max(0, bestProb) };
}

/**
 * 把一只狼的 `god_role_intel` 展平为按威胁降序的行列表。
 * 同威胁按目标座位升序，保证确定性。空/缺字段 → []。
 */
export function selectGodRoleRows(record: WolfCampMindV2 | null | undefined): GodRoleRow[] {
  const intel = record?.god_role_intel;
  if (!intel) return [];

  const rows: GodRoleRow[] = Object.values(intel).map((b) => {
    const distribution = {} as Record<GodRole, number>;
    for (const role of GOD_ROLES) {
      distribution[role] = Number(b.role_distribution?.[role] ?? 0);
    }
    const top = topRoleOf(distribution);
    return {
      targetSeat: b.target_seat,
      distribution,
      topRole: top.role,
      topProb: top.prob,
      threat: Number(b.threat_score ?? 0),
      priority: (b.priority ?? "low") as GodRolePriority,
      evidence: Array.isArray(b.evidence) ? b.evidence : [],
    };
  });

  return rows.sort((a, b) => b.threat - a.threat || a.targetSeat - b.targetSeat);
}

/** 单个目标的全 0 神职信念（初始骨架格）。 */
export function zeroBelief(targetSeat: number, round: number): GodRoleBeliefV2 {
  const role_distribution = {} as Record<GodRole, number>;
  for (const role of GOD_ROLES) role_distribution[role] = 0;
  return {
    target_seat: targetSeat,
    role_distribution,
    threat_score: 0,
    priority: "low",
    evidence: [],
    updated_round: round,
    contributors: [],
  };
}

/**
 * 从 roster 派生「每只存活狼 × 每个存活非狼目标」的神职矩阵骨架（全 0），
 * 并用 store 中各狼的真实 god_role_intel 覆盖已预测的目标行；未预测的目标保持 0。
 * 无存活狼 → []。
 */
export function selectWolfMatrices(
  players: { seat: number; camp: string; alive: boolean }[] | null | undefined,
  minds: Record<number, WolfCampMindV2> | null | undefined,
  round: number,
): WolfCampMindV2[] {
  if (!players || players.length === 0) return [];
  const wolves = players
    .filter((p) => p.camp === "werewolf" && p.alive)
    .sort((a, b) => a.seat - b.seat);
  if (wolves.length === 0) return [];
  const targets = players
    .filter((p) => p.camp !== "werewolf" && p.alive)
    .sort((a, b) => a.seat - b.seat);

  return wolves.map((wolf) => {
    const existing = minds?.[wolf.seat];
    const god_role_intel: Record<string, GodRoleBeliefV2> = {};
    for (const t of targets) {
      const key = String(t.seat);
      god_role_intel[key] = existing?.god_role_intel?.[key] ?? zeroBelief(t.seat, round);
    }
    return {
      schema: "wolf_camp_mind_v2",
      owner_seat: wolf.seat,
      round,
      contributor_seat: wolf.seat,
      god_role_intel,
      exposure_radar: existing?.exposure_radar ?? {},
    };
  });
}
