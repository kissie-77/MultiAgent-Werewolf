// Role art is served from `frontend/public/{material,tarot}/<PascalCase>.png`.
//（与后端角色名匹配的规范词干）。作为纯绝对 URL 引用 — 不要从 `public/` 导入（Vite 会返回 SPA 回退 HTML）。
// `material` = 对局内肖像，`tarot` = 开局塔罗牌。

// 角色字符串（英文阵容角色名，去除空格，或中文显示名）-> 规范词干
const ROLE_STEM: Record<string, string> = {
  // --- 英文（后端阵容角色名，stemFor 已去除空格）---
  Werewolf: "Werewolf", AlphaWolf: "AlphaWolf", WhiteWolf: "WhiteWolf", WolfBeauty: "WolfBeauty",
  GuardianWolf: "GuardianWolf", HiddenWolf: "HiddenWolf", BloodMoonApostle: "BloodMoonApostle",
  NightmareWolf: "NightmareWolf",
  Villager: "Villager", Seer: "Seer", Witch: "Witch", Hunter: "Hunter", Guard: "Guard",
  Idiot: "Idiot", Elder: "Elder", Knight: "Knight", Magician: "Magician", Cupid: "Cupid",
  Raven: "Raven", GraveyardKeeper: "GraveyardKeeper", Thief: "Thief", Lover: "Lover",
  // --- 中文（UI 显示名 / 设置下拉值）---
  狼人: "Werewolf", 狼王: "AlphaWolf", 白狼: "WhiteWolf", 狼美人: "WolfBeauty", 守卫狼: "GuardianWolf",
  隐狼: "HiddenWolf", 血月使徒: "BloodMoonApostle", 梦魇狼: "NightmareWolf",
  村民: "Villager", 平民: "Villager", 预言家: "Seer", 女巫: "Witch", 猎人: "Hunter", 守卫: "Guard",
  白痴: "Idiot", 长老: "Elder", 骑士: "Knight", 魔术师: "Magician", 丘比特: "Cupid", 乌鸦: "Raven",
  守墓人: "GraveyardKeeper", 盗贼: "Thief", 恋人: "Lover",
};

/** 后端可能返回小写角色名，统一映射到 PascalCase 词干。 */
const LOWERCASE_STEM: Record<string, string> = {
  werewolf: "Werewolf", alphawolf: "AlphaWolf", whitewolf: "WhiteWolf", wolfbeauty: "WolfBeauty",
  guardianwolf: "GuardianWolf", hiddenwolf: "HiddenWolf", bloodmoonapostle: "BloodMoonApostle",
  nightmarewolf: "NightmareWolf",
  villager: "Villager", seer: "Seer", witch: "Witch", hunter: "Hunter", guard: "Guard",
  idiot: "Idiot", elder: "Elder", knight: "Knight", magician: "Magician", cupid: "Cupid",
  raven: "Raven", graveyardkeeper: "GraveyardKeeper", thief: "Thief", lover: "Lover",
  wolf: "Werewolf",
};

function stemFor(role: string): string {
  const raw = role ?? "";
  const key = raw.replace(/\s+/g, ""); // "Alpha Wolf" -> "AlphaWolf"
  if (ROLE_STEM[key]) return ROLE_STEM[key];
  if (ROLE_STEM[raw]) return ROLE_STEM[raw];
  // 尝试小写匹配（后端可能返回 "seer"、"werewolf" 等）
  const lowerKey = key.toLowerCase();
  if (LOWERCASE_STEM[lowerKey]) return LOWERCASE_STEM[lowerKey];
  if (lowerKey.includes("wolf") || raw.includes("狼")) return "Werewolf";
  return "Villager";
}

export const getRoleImage = (role: string) => `/material/${stemFor(role)}.png`;
export const getTarotImage = (role: string) => `/tarot/${stemFor(role)}.png`;
