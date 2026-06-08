import { describe, it, expect } from "vitest";
import { effectTypeForRole, skillMetaForRole, castFromEvent, effectTypeForEvent } from "./castMap";

describe("effectTypeForRole", () => {
  it("maps wolf camp to bite", () => {
    expect(effectTypeForRole("狼人")).toBe("bite");
    expect(effectTypeForRole("Werewolf")).toBe("bite");
  });
  it("maps seer to inspect, witch to heal, hunter to shoot", () => {
    expect(effectTypeForRole("预言家")).toBe("inspect");
    expect(effectTypeForRole("女巫")).toBe("heal");
    expect(effectTypeForRole("猎人")).toBe("shoot");
  });
  it("defaults villager to vote", () => {
    expect(effectTypeForRole("村民")).toBe("vote");
  });
});

describe("skillMetaForRole", () => {
  it("returns a name + sub for known roles", () => {
    const m = skillMetaForRole("预言家");
    expect(m.skillName).toBeTruthy();
    expect(m.skillSub).toBeTruthy();
  });
});

describe("castFromEvent", () => {
  it("builds a cast from role_acting with a role", () => {
    const cast = castFromEvent({
      event_type: "role_acting",
      data: { player_id: "player_3", player_name: "Player3", role: "预言家" },
    });
    expect(cast).not.toBeNull();
    expect(cast!.casterId).toBe(3);
    expect(cast!.effectType).toBe("inspect");
  });
  it("returns null when role is hidden (redacted)", () => {
    expect(
      castFromEvent({
        event_type: "role_acting",
        data: { player_id: "player_3", role: "" },
      })
    ).toBeNull();
  });
  it("returns null for unrelated events", () => {
    expect(castFromEvent({ event_type: "phase_changed", data: {} })).toBeNull();
  });
});

describe("effectTypeForEvent", () => {
  it("distinguishes witch poison vs save", () => {
    expect(effectTypeForEvent("witch_poison_used")).toBe("poison");
    expect(effectTypeForEvent("witch_saved")).toBe("heal");
  });
  it("maps special skills", () => {
    expect(effectTypeForEvent("raven_marked")).toBe("mark");
    expect(effectTypeForEvent("knight_duel")).toBe("duel");
    expect(effectTypeForEvent("graveyard_keeper_check")).toBe("corpse");
    expect(effectTypeForEvent("nightmare_blocked")).toBe("fear");
  });
  it("ignores vote_cast and unknowns", () => {
    expect(effectTypeForEvent("vote_cast")).toBeNull();
    expect(effectTypeForEvent("phase_changed")).toBeNull();
  });
});

describe("effectTypeForRole (expanded)", () => {
  it("maps the newly covered roles", () => {
    expect(effectTypeForRole("守卫")).toBe("guard");
    expect(effectTypeForRole("乌鸦")).toBe("mark");
    expect(effectTypeForRole("丘比特")).toBe("link");
    expect(effectTypeForRole("骑士")).toBe("duel");
    expect(effectTypeForRole("守墓人")).toBe("corpse");
  });
  it("keeps wolves as bite", () => {
    expect(effectTypeForRole("狼美人")).toBe("bite");
    expect(effectTypeForRole("Werewolf")).toBe("bite");
  });
});
