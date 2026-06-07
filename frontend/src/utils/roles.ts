// Role portraits: tarot deck in `frontend/public/tarot/` (served at `/tarot/*.png`).
// Fallback to `public/material/` for legacy paths.
const seerImg = "/tarot/seer.png";
const witchImg = "/tarot/witch.png";
const hunterImg = "/tarot/hunter.png";
const wolfImg = "/tarot/wolf.png";
const villagerImg = "/tarot/villager.png";

export const roleImageMap: Record<string, string> = {
  // --- Catalog keys (backend RoleListItem.key) ---
  Seer: seerImg,
  Witch: witchImg,
  Hunter: hunterImg,
  Werewolf: wolfImg,
  AlphaWolf: "/tarot/AlphaWolf.png",
  WhiteWolf: "/tarot/WhiteWolf.png",
  WolfBeauty: "/tarot/WolfBeauty.png",
  GuardianWolf: "/tarot/GuardianWolf.png",
  HiddenWolf: "/tarot/HiddenWolf.png",
  NightmareWolf: "/tarot/NightmareWolf.png",
  BloodMoonApostle: "/tarot/BloodMoonApostle.png",
  Villager: villagerImg,
  Guard: "/tarot/Guard.png",
  Idiot: "/tarot/idiot.png",
  Elder: "/tarot/Elder.png",
  Knight: villagerImg,
  Magician: "/tarot/Magician.png",
  Cupid: "/tarot/Cupid.png",
  Raven: "/tarot/Raven.png",
  GraveyardKeeper: "/tarot/GraveyardKeeper.png",
  Thief: "/tarot/Thief.png",
  Lover: "/tarot/Lover.png",
  // --- Runtime / English names ---
  "Alpha Wolf": "/tarot/AlphaWolf.png",
  "White Wolf": "/tarot/WhiteWolf.png",
  "Wolf Beauty": "/tarot/WolfBeauty.png",
  "Guardian Wolf": "/tarot/GuardianWolf.png",
  "Hidden Wolf": "/tarot/HiddenWolf.png",
  "Nightmare Wolf": "/tarot/NightmareWolf.png",
  "Blood Moon Apostle": "/tarot/BloodMoonApostle.png",
  "Graveyard Keeper": "/tarot/GraveyardKeeper.png",
  // --- Chinese display names ---
  预言家: seerImg,
  女巫: witchImg,
  猎人: hunterImg,
  狼人: wolfImg,
  狼王: "/tarot/AlphaWolf.png",
  白狼: "/tarot/WhiteWolf.png",
  狼美人: "/tarot/WolfBeauty.png",
  守卫狼: "/tarot/GuardianWolf.png",
  隐狼: "/tarot/HiddenWolf.png",
  血月使徒: "/tarot/BloodMoonApostle.png",
  梦魇狼: "/tarot/NightmareWolf.png",
  守卫: "/tarot/Guard.png",
  白痴: "/tarot/idiot.png",
  长老: "/tarot/Elder.png",
  骑士: villagerImg,
  魔术师: "/tarot/Magician.png",
  丘比特: "/tarot/Cupid.png",
  乌鸦: "/tarot/Raven.png",
  守墓人: "/tarot/GraveyardKeeper.png",
  盗贼: "/tarot/Thief.png",
  恋人: "/tarot/Lover.png",
  村民: villagerImg,
  平民: villagerImg,
};

export const getRoleImage = (role: string) => {
  const exact = roleImageMap[role];
  if (exact) return exact;
  if ((role ?? "").toLowerCase().includes("wolf") || (role ?? "").includes("狼")) return wolfImg;
  return villagerImg;
};
