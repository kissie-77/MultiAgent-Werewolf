// Role art is served from `frontend/public/{material,tarot}/<PascalCase>.png`
// (canonical stems matching the backend role names). Reference as plain absolute
// URLs — do NOT `import` from `public/` (Vite returns SPA-fallback HTML).
// `material` = in-game portrait, `tarot` = setup arcana card.

// role string (English roster name, space-stripped, OR Chinese display name) -> canonical stem
const ROLE_STEM: Record<string, string> = {
  // --- English (backend roster role_name, spaces stripped by stemFor) ---
  Werewolf: "Werewolf", AlphaWolf: "AlphaWolf", WhiteWolf: "WhiteWolf", WolfBeauty: "WolfBeauty",
  GuardianWolf: "GuardianWolf", HiddenWolf: "HiddenWolf", BloodMoonApostle: "BloodMoonApostle",
  NightmareWolf: "NightmareWolf",
  Villager: "Villager", Seer: "Seer", Witch: "Witch", Hunter: "Hunter", Guard: "Guard",
  Idiot: "Idiot", Elder: "Elder", Knight: "Knight", Magician: "Magician", Cupid: "Cupid",
  Raven: "Raven", GraveyardKeeper: "GraveyardKeeper", Thief: "Thief", Lover: "Lover",
  // --- Chinese (in-UI display names / setup dropdown values) ---
  狼人: "Werewolf", 狼王: "AlphaWolf", 白狼: "WhiteWolf", 狼美人: "WolfBeauty", 守卫狼: "GuardianWolf",
  隐狼: "HiddenWolf", 血月使徒: "BloodMoonApostle", 梦魇狼: "NightmareWolf",
  村民: "Villager", 平民: "Villager", 预言家: "Seer", 女巫: "Witch", 猎人: "Hunter", 守卫: "Guard",
  白痴: "Idiot", 长老: "Elder", 骑士: "Knight", 魔术师: "Magician", 丘比特: "Cupid", 乌鸦: "Raven",
  守墓人: "GraveyardKeeper", 盗贼: "Thief", 恋人: "Lover",
};

/** Legacy lowercase filenames kept alongside PascalCase assets in `public/material`. */
const MATERIAL_LEGACY_FILE: Record<string, string> = {
  Seer: "seer",
  Witch: "witch",
  Hunter: "hunter",
  Werewolf: "wolf",
};

function stemFor(role: string): string {
  const raw = role ?? "";
  const key = raw.replace(/\s+/g, ""); // "Alpha Wolf" -> "AlphaWolf"
  if (ROLE_STEM[key]) return ROLE_STEM[key];
  if (ROLE_STEM[raw]) return ROLE_STEM[raw];
  if (key.toLowerCase().includes("wolf") || raw.includes("狼")) return "Werewolf";
  return "Villager";
}

function materialFile(stem: string): string {
  return MATERIAL_LEGACY_FILE[stem] ?? stem;
}

export const getRoleImage = (role: string) => `/material/${materialFile(stemFor(role))}.png`;
export const getTarotImage = (role: string) => `/tarot/${stemFor(role)}.png`;
