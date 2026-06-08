import type { ActiveCast, EffectType } from "../types";

const WOLF_CAMP = [
  "狼人", "狼王", "白狼", "白狼王", "狼美人", "守卫狼", "隐狼", "血月使徒", "梦魇狼",
];

function isWolf(role: string): boolean {
  const r = role.toLowerCase();
  return WOLF_CAMP.some((w) => role.includes(w)) || r.includes("wolf") || r.includes("werewolf");
}

export function effectTypeForRole(role: string): EffectType {
  if (!role) return "rally";
  if (isWolf(role)) return "bite";
  const r = role.toLowerCase();
  if (role.includes("预言") || r.includes("seer") || r.includes("prophet")) return "inspect";
  if (role.includes("女巫") || r.includes("witch")) return "heal";
  if (role.includes("猎人") || r.includes("hunter")) return "shoot";
  if (role.includes("守墓") || r.includes("graveyard")) return "corpse";
  if (role.includes("守卫") || r.includes("guard")) return "guard";
  if (role.includes("骑士") || r.includes("knight")) return "duel";
  if (role.includes("魔术") || r.includes("magician")) return "swap";
  if (role.includes("乌鸦") || r.includes("raven")) return "mark";
  if (role.includes("丘比特") || r.includes("cupid")) return "link";
  if (role.includes("村民") || r.includes("villager")) return "vote";
  return "rally";
}

/** 后端技能结果事件 → effectType（声音用；不含 vote_cast）。 */
const SKILL_EVENT_EFFECT: Record<string, EffectType> = {
  seer_checked: "inspect",
  witch_saved: "heal",
  witch_poison_used: "poison",
  witch_poisoned: "poison",
  werewolf_killed: "bite",
  hunter_revenge: "shoot",
  white_wolf_killed: "shoot",
  guard_protected: "guard",
  guardian_wolf_protected: "guard",
  wolf_beauty_charmed: "charm",
  raven_marked: "mark",
  lovers_linked: "link",
  knight_duel: "duel",
  magician_swapped: "swap",
  graveyard_keeper_check: "corpse",
  nightmare_blocked: "fear",
};

export function effectTypeForEvent(eventType: string): EffectType | null {
  return SKILL_EVENT_EFFECT[eventType] ?? null;
}

export function skillMetaForRole(role: string): { skillName: string; skillSub: string } {
  const e = effectTypeForRole(role);
  switch (e) {
    case "bite": return { skillName: "狼人袭击", skillSub: "獠牙撕裂黑夜" };
    case "inspect": return { skillName: "预言查验", skillSub: "窥探灵魂真伪" };
    case "heal": return { skillName: "女巫施药", skillSub: "解药 / 毒药" };
    case "shoot": return { skillName: "猎人开枪", skillSub: "临终一击" };
    case "vote": return { skillName: "投票表决", skillSub: "民意裁断" };
    default: return { skillName: "神秘技能", skillSub: "命运之手" };
  }
}

function seatFrom(data: Record<string, unknown> | undefined): number | null {
  const pid = (data?.player_id ?? data?.shooter_id ?? data?.voter_id) as string | undefined;
  if (typeof pid === "string") {
    const m = pid.match(/(\d+)$/);
    if (m) return Number(m[1]);
  }
  if (typeof data?.seat === "number") return data.seat as number;
  return null;
}

/** Build an ActiveCast from an SSE skill-cast / reveal event, or null if not applicable / role hidden. */
export function castFromEvent(ev: {
  event_type: string;
  data?: Record<string, unknown>;
}): ActiveCast | null {
  const t = ev.event_type;
  if (t !== "role_acting" && t !== "role_revealed") return null;
  const role = String(ev.data?.role ?? "");
  if (!role) return null; // redacted in seat view -> no reveal
  const seat = seatFrom(ev.data);
  if (seat == null) return null;
  const meta = skillMetaForRole(role);
  return {
    casterId: seat,
    casterName: String(ev.data?.player_name ?? `Player${seat}`),
    role,
    skillName: t === "role_revealed" ? "身份揭示" : meta.skillName,
    skillSub: t === "role_revealed" ? role : meta.skillSub,
    targetId: null,
    targetName: null,
    effectType: effectTypeForRole(role),
  };
}

/** Build an ActiveCast for the seated human's own skill submission. */
export function castFromSkillSubmit(args: {
  selfRole: string;
  selfName: string;
  targetSeat: number | null;
  targetName: string | null;
}): ActiveCast {
  const meta = skillMetaForRole(args.selfRole);
  return {
    casterId: "USER",
    casterName: args.selfName,
    role: args.selfRole,
    skillName: meta.skillName,
    skillSub: meta.skillSub,
    targetId: args.targetSeat,
    targetName: args.targetName,
    effectType: effectTypeForRole(args.selfRole),
  };
}
