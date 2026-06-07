import { describe, it, expect } from "vitest";
import { getRoleImage, getTarotImage } from "./roles";

describe("role image resolution", () => {
  it("Chinese setup roles -> tarot", () => {
    expect(getTarotImage("白痴")).toBe("/tarot/Idiot.png");
    expect(getTarotImage("预言家")).toBe("/tarot/Seer.png");
    expect(getTarotImage("村民")).toBe("/tarot/Villager.png");
  });
  it("English roster roles -> material (legacy lowercase filenames)", () => {
    expect(getRoleImage("Witch")).toBe("/material/witch.png");
    expect(getRoleImage("Werewolf")).toBe("/material/wolf.png");
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
    expect(getRoleImage("狼人")).toBe("/material/wolf.png");
    expect(getRoleImage("???")).toBe("/material/Villager.png");
    expect(getRoleImage("")).toBe("/material/Villager.png");
  });
});
