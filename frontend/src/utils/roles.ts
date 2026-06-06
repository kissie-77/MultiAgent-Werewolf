// Role portraits live in `frontend/public/material/` and are served by Vite at
// the site root (`/material/*.png`). Do NOT `import` them from `public/` — Vite
// does not bundle public assets and resolves such imports to an unserved
// `/public/material/*.png` URL (SPA-fallback HTML, naturalWidth=0). Reference
// them as plain absolute URLs instead.
const seerImg = "/material/seer.png";
const witchImg = "/material/witch.png";
const hunterImg = "/material/hunter.png";
const wolfImg = "/material/wolf.png";
const villagerImg = "/material/villiger.png";

// Keyed by BOTH the backend's English roster role names (god_roster.json /
// roster: "Seer" / "Werewolf" / "Witch" / "Villager" ...) AND the Chinese role
// names used elsewhere in the UI. Only 5 portraits exist, so generic good-camp
// roles share the villager art and all wolf variants share the wolf art.
export const roleImageMap: Record<string, string> = {
  // --- English (backend roster role_name) ---
  Seer: seerImg,
  Witch: witchImg,
  Hunter: hunterImg,
  Werewolf: wolfImg,
  AlphaWolf: wolfImg,
  WhiteWolf: wolfImg,
  WolfBeauty: wolfImg,
  GuardianWolf: wolfImg,
  HiddenWolf: wolfImg,
  NightmareWolf: wolfImg,
  BloodMoonApostle: wolfImg,
  Villager: villagerImg,
  Guard: villagerImg,
  Idiot: villagerImg,
  Elder: villagerImg,
  Knight: villagerImg,
  Magician: villagerImg,
  Cupid: villagerImg,
  Raven: villagerImg,
  GraveyardKeeper: villagerImg,
  Thief: villagerImg,
  Lover: villagerImg,
  // --- Chinese (in-UI display names) ---
  预言家: seerImg,
  女巫: witchImg,
  猎人: hunterImg,
  狼人: wolfImg,
  狼王: wolfImg,
  白狼: wolfImg,
  狼美人: wolfImg,
  守卫狼: wolfImg,
  隐狼: wolfImg,
  血月使徒: wolfImg,
  梦魇狼: wolfImg,
  守卫: villagerImg,
  白痴: villagerImg,
  长老: villagerImg,
  骑士: villagerImg,
  魔术师: villagerImg,
  丘比特: villagerImg,
  乌鸦: villagerImg,
  守墓人: villagerImg,
  盗贼: villagerImg,
  恋人: villagerImg,
  村民: villagerImg,
  平民: villagerImg,
};

export const getRoleImage = (role: string) => {
  const exact = roleImageMap[role];
  if (exact) return exact;
  // Unknown role / camp string ("werewolf", a wolf variant, etc.): any wolf -> wolf art.
  if ((role ?? "").toLowerCase().includes("wolf") || (role ?? "").includes("狼")) return wolfImg;
  return villagerImg;
};
