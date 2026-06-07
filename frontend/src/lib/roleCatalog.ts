import type { BoardPresetOption, PlayableRoleOption } from "../api/types";

/** 22 种可玩身份（API 未就绪时的本地兜底） */
export const FALLBACK_PLAYABLE_ROLES: PlayableRoleOption[] = [
  { key: "Werewolf", display_name: "狼人", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "AlphaWolf", display_name: "狼王", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "WhiteWolf", display_name: "白狼", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "WolfBeauty", display_name: "狼美人", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "GuardianWolf", display_name: "守卫狼", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "HiddenWolf", display_name: "隐狼", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "BloodMoonApostle", display_name: "血月使徒", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "NightmareWolf", display_name: "梦魇狼", camp: "werewolf", camp_label: "狼人阵营" },
  { key: "Villager", display_name: "平民", camp: "villager", camp_label: "好人阵营" },
  { key: "Seer", display_name: "预言家", camp: "villager", camp_label: "好人阵营" },
  { key: "Witch", display_name: "女巫", camp: "villager", camp_label: "好人阵营" },
  { key: "Hunter", display_name: "猎人", camp: "villager", camp_label: "好人阵营" },
  { key: "Guard", display_name: "守卫", camp: "villager", camp_label: "好人阵营" },
  { key: "Idiot", display_name: "白痴", camp: "villager", camp_label: "好人阵营" },
  { key: "Elder", display_name: "长老", camp: "villager", camp_label: "好人阵营" },
  { key: "Knight", display_name: "骑士", camp: "villager", camp_label: "好人阵营" },
  { key: "Magician", display_name: "魔术师", camp: "villager", camp_label: "好人阵营" },
  { key: "Raven", display_name: "乌鸦", camp: "villager", camp_label: "好人阵营" },
  { key: "GraveyardKeeper", display_name: "守墓人", camp: "villager", camp_label: "好人阵营" },
  { key: "Cupid", display_name: "丘比特", camp: "neutral", camp_label: "第三方" },
  { key: "Thief", display_name: "盗贼", camp: "neutral", camp_label: "第三方" },
  { key: "Lover", display_name: "恋人", camp: "neutral", camp_label: "第三方" },
];

export function effectivePlayableRoles(roles: PlayableRoleOption[]): PlayableRoleOption[] {
  return roles.length > 0 ? roles : FALLBACK_PLAYABLE_ROLES;
}

export function sortedRoleOptions(roles: PlayableRoleOption[]): PlayableRoleOption[] {
  const campOrder = { werewolf: 0, villager: 1, neutral: 2 };
  return [...effectivePlayableRoles(roles)].sort((a, b) => {
    const ca = campOrder[a.camp as keyof typeof campOrder] ?? 9;
    const cb = campOrder[b.camp as keyof typeof campOrder] ?? 9;
    if (ca !== cb) return ca - cb;
    return a.display_name.localeCompare(b.display_name, "zh");
  });
}

/** Catalog key -> 中文显示名 */
export function roleDisplayName(
  key: string,
  roles: PlayableRoleOption[] = [],
): string {
  const pool = effectivePlayableRoles(roles);
  const hit = pool.find((r) => r.key === key);
  return hit?.display_name ?? key;
}

export function roleOptionLabel(role: PlayableRoleOption): string {
  return `${role.display_name} · ${role.camp_label}`;
}

export function lineupSummary(
  roleNames: string[],
  roles: PlayableRoleOption[] = [],
): string {
  const pool = effectivePlayableRoles(roles);
  const counts = new Map<string, number>();
  for (const key of roleNames) {
    const label = roleDisplayName(key, pool);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([label, n]) => (n > 1 ? `${label}×${n}` : label))
    .join(" · ");
}

export function standardLineupForCount(count: number): string[] {
  const wolves =
    count <= 8 ? 2 : count <= 11 ? 3 : count <= 14 ? 4 : 5;
  const specials: string[] = ["Seer", "Witch"];
  if (count >= 7) specials.push("Guard");
  if (count >= 9) specials.push("Hunter");
  if (count >= 11) specials.push("Cupid");
  if (count >= 13) specials.push("Idiot");
  if (count >= 15) specials.push("Elder");
  if (count >= 17) specials.push("Knight");
  if (count >= 19) specials.push("Raven");
  const wolfKeys =
    count <= 8
      ? ["Werewolf", "Werewolf"]
      : count <= 11
        ? ["Werewolf", "Werewolf", "AlphaWolf"]
        : count <= 14
          ? ["Werewolf", "Werewolf", "AlphaWolf", "WhiteWolf"]
          : ["Werewolf", "Werewolf", "AlphaWolf", "WhiteWolf", "WolfBeauty"];
  const villagers = Math.max(0, count - wolfKeys.length - specials.length);
  return [...wolfKeys.slice(0, wolves), ...specials, ...Array(villagers).fill("Villager")];
}

export function validateCustomLineup(roleNames: string[], roles: PlayableRoleOption[]): string | null {
  if (roleNames.length < 6 || roleNames.length > 20) {
    return "人数须在 6–20 之间";
  }
  const pool = effectivePlayableRoles(roles);
  const wolfKeys = new Set(pool.filter((r) => r.camp === "werewolf").map((r) => r.key));
  if (!roleNames.some((k) => wolfKeys.has(k))) {
    return "阵容至少需要一名狼人阵营角色";
  }
  return null;
}

export function presetsByKind(presets: BoardPresetOption[]) {
  return {
    curated: presets.filter((p) => p.kind === "curated"),
    standard: presets.filter((p) => p.kind === "standard"),
  };
}

export function findPreset(presets: BoardPresetOption[], id: string): BoardPresetOption | undefined {
  return presets.find((p) => p.preset_id === id);
}
