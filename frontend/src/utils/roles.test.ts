import { describe, it, expect } from "vitest";
import { readdirSync } from "node:fs";
import { join } from "node:path";
import { getRoleImage, getTarotImage } from "./roles";

const PUBLIC_ROOT = join(import.meta.dirname, "../../public");
const MATERIAL_DIR = join(PUBLIC_ROOT, "material");
const TAROT_DIR = join(PUBLIC_ROOT, "tarot");

const ALL_STEMS = [
  "Werewolf", "AlphaWolf", "WhiteWolf", "WolfBeauty", "GuardianWolf", "HiddenWolf",
  "BloodMoonApostle", "NightmareWolf", "Villager", "Seer", "Witch", "Hunter", "Guard",
  "Idiot", "Elder", "Knight", "Magician", "Cupid", "Raven", "GraveyardKeeper", "Thief", "Lover",
];

describe("role image resolution", () => {
  it("Chinese setup roles -> tarot", () => {
    expect(getTarotImage("白痴")).toBe("/tarot/Idiot.png");
    expect(getTarotImage("预言家")).toBe("/tarot/Seer.png");
    expect(getTarotImage("村民")).toBe("/tarot/Villager.png");
  });

  it("English roster roles -> material (PascalCase filenames)", () => {
    expect(getRoleImage("Witch")).toBe("/material/Witch.png");
    expect(getRoleImage("Werewolf")).toBe("/material/Werewolf.png");
  });

  it("strips spaces in English names", () => {
    expect(getRoleImage("Alpha Wolf")).toBe("/material/AlphaWolf.png");
    expect(getTarotImage("Graveyard Keeper")).toBe("/tarot/GraveyardKeeper.png");
  });

  it("idiot is distinct from villager (the original bug)", () => {
    expect(getTarotImage("白痴")).not.toBe(getTarotImage("村民"));
    expect(getRoleImage("白痴")).toBe("/material/Idiot.png");
  });

  it("unknown wolf-ish -> Werewolf, else Villager", () => {
    expect(getRoleImage("狼人")).toBe("/material/Werewolf.png");
    expect(getRoleImage("???")).toBe("/material/Villager.png");
    expect(getRoleImage("")).toBe("/material/Villager.png");
  });

  it("every canonical stem has assets under public/material and public/tarot", () => {
    const material = new Set(readdirSync(MATERIAL_DIR));
    const tarot = new Set(readdirSync(TAROT_DIR));
    for (const stem of ALL_STEMS) {
      expect(material.has(`${stem}.png`), `missing material/${stem}.png`).toBe(true);
      expect(tarot.has(`${stem}.png`), `missing tarot/${stem}.png`).toBe(true);
    }
  });
});
