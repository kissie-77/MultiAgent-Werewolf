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
    case "poison": return { skillName: "女巫毒药", skillSub: "剧毒蚀骨" };
    case "shoot": return { skillName: "猎人开枪", skillSub: "临终一击" };
    case "vote": return { skillName: "投票表决", skillSub: "民意裁断" };
    case "guard": return { skillName: "守卫守护", skillSub: "以身御灾" };
    case "charm": return { skillName: "狼美人魅惑", skillSub: "致命之吻" };
    case "mark": return { skillName: "乌鸦标记", skillSub: "不祥之印" };
    case "link": return { skillName: "丘比特连心", skillSub: "命运红线" };
    case "duel": return { skillName: "骑士决斗", skillSub: "荣耀对决" };
    case "swap": return { skillName: "魔术换牌", skillSub: "偷天换日" };
    case "corpse": return { skillName: "守墓查验", skillSub: "亡者低语" };
    case "fear": return { skillName: "梦魇封锁", skillSub: "噩梦缠身" };
    default: return { skillName: "神秘技能", skillSub: "命运之手" };
  }
}

/** Verb shown on the caster→target line for the seated human's own action. */
function verbForEffect(e: EffectType): string {
  switch (e) {
    case "bite": return "击杀";
    case "inspect": return "查验";
    case "heal": return "救治";
    case "poison": return "毒杀";
    case "shoot": return "开枪击杀";
    case "vote": return "投票";
    default: return "指向";
  }
}

/** Parse a 1-based seat from an id like "player_5", or a bare number. */
function seatFromId(pid: unknown): number | null {
  if (typeof pid === "string") {
    const m = pid.match(/(\d+)$/);
    if (m) return Number(m[1]);
  }
  if (typeof pid === "number") return pid;
  return null;
}

function seatFrom(data: Record<string, unknown> | undefined): number | null {
  return (
    seatFromId(data?.player_id ?? data?.shooter_id ?? data?.voter_id) ??
    (typeof data?.seat === "number" ? (data.seat as number) : null)
  );
}

/** Resolve a seat to a display name from the live roster, falling back to "<n>号". */
function nameForSeat(seat: number, players?: { id: number; name: string }[]): string {
  return players?.find((p) => p.id === seat)?.name ?? `${seat}号`;
}

/**
 * Backend skill-RESULT event_type -> tarot card metadata. These are the meaningful
 * "skill landed" moments that carry a target; god view sees them all, so the card
 * can show「击杀了 Player5」etc. (mirrors the retired NightSkillOverlay table).
 */
const RESULT_CAST: Record<
  string,
  { role: string; skillName: string; skillSub: string; verb: string; effectType?: EffectType }
> = {
  werewolf_killed: { role: "狼人", skillName: "狼人袭击", skillSub: "獠牙撕裂黑夜", verb: "击杀" },
  white_wolf_killed: { role: "白狼", skillName: "白狼出刀", skillSub: "自爆的獠牙", verb: "击杀" },
  seer_checked: { role: "预言家", skillName: "预言查验", skillSub: "窥探灵魂真伪", verb: "查验" },
  witch_saved: { role: "女巫", skillName: "女巫解药", skillSub: "起死回生", verb: "救治", effectType: "heal" },
  witch_poison_used: { role: "女巫", skillName: "女巫毒药", skillSub: "剧毒蚀骨", verb: "毒杀", effectType: "poison" },
  witch_poisoned: { role: "女巫", skillName: "女巫毒药", skillSub: "剧毒蚀骨", verb: "毒杀", effectType: "poison" },
  guard_protected: { role: "守卫", skillName: "守卫守护", skillSub: "以身御灾", verb: "守护", effectType: "heal" },
  guardian_wolf_protected: { role: "守卫狼", skillName: "守卫狼守护", skillSub: "暗影庇护", verb: "保护" },
  hunter_revenge: { role: "猎人", skillName: "猎人开枪", skillSub: "临终一击", verb: "开枪击杀", effectType: "shoot" },
  lovers_linked: { role: "丘比特", skillName: "丘比特连心", skillSub: "命运红线", verb: "连结", effectType: "link" },
  wolf_beauty_charmed: { role: "狼美人", skillName: "狼美人魅惑", skillSub: "致命之吻", verb: "魅惑" },
  nightmare_blocked: { role: "梦魇狼", skillName: "梦魇封锁", skillSub: "噩梦缠身", verb: "封锁" },
  knight_duel: { role: "骑士", skillName: "骑士决斗", skillSub: "荣耀对决", verb: "决斗", effectType: "duel" },
  raven_marked: { role: "乌鸦", skillName: "乌鸦标记", skillSub: "不祥之印", verb: "标记", effectType: "vote" },
  graveyard_keeper_check: { role: "守墓人", skillName: "守墓查验", skillSub: "亡者低语", verb: "查验", effectType: "inspect" },
  magician_swapped: { role: "魔术师", skillName: "魔术师换牌", skillSub: "偷天换日", verb: "交换", effectType: "rally" },
};

/**
 * Build an ActiveCast from an SSE event, or null if not applicable.
 * Driven by skill-RESULT events (they carry the target) plus `role_revealed`
 * (身份揭示, no target). `players` resolves seat ids to display names.
 */
export function castFromEvent(
  ev: { event_type: string; data?: Record<string, unknown> },
  players?: { id: number; name: string }[],
): ActiveCast | null {
  const t = ev.event_type;
  const data = ev.data ?? {};

  if (t === "role_revealed") {
    const role = String(data.role ?? "");
    if (!role) return null; // redacted in seat view -> no reveal
    const seat = seatFrom(data);
    if (seat == null) return null;
    return {
      casterId: seat,
      casterName: String(data.player_name ?? `Player${seat}`),
      role,
      skillName: "身份揭示",
      skillSub: role,
      targetId: null,
      targetName: null,
      targetVerb: "",
      effectType: effectTypeForRole(role),
    };
  }

  const m = RESULT_CAST[t];
  if (!m) return null;

  const targetId =
    seatFromId(data.target_id) ?? (typeof data.target_seat === "number" ? (data.target_seat as number) : null);
  const targetName =
    (typeof data.target_name === "string" && data.target_name) ||
    (targetId != null ? nameForSeat(targetId, players) : null);

  const casterId = seatFromId(data.player_id);
  const casterName = casterId != null ? nameForSeat(casterId, players) : m.role; // team kill -> role name

  return {
    casterId: casterId ?? -1,
    casterName,
    role: m.role,
    skillName: m.skillName,
    skillSub: m.skillSub,
    targetId,
    targetName,
    targetVerb: m.verb,
    effectType: m.effectType ?? effectTypeForRole(m.role),
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
  const effectType = effectTypeForRole(args.selfRole);
  return {
    casterId: "USER",
    casterName: args.selfName,
    role: args.selfRole,
    skillName: meta.skillName,
    skillSub: meta.skillSub,
    targetId: args.targetSeat,
    targetName: args.targetName,
    targetVerb: args.targetSeat != null ? verbForEffect(effectType) : "",
    effectType,
  };
}
