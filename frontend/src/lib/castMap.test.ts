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

const PLAYERS = [
  { id: 2, name: "Bob" },
  { id: 5, name: "Eve" },
] as { id: number; name: string }[];

describe("castFromEvent (result-event driven)", () => {
  it("builds a cast from werewolf_killed with target carried on the event", () => {
    const cast = castFromEvent({
      event_type: "werewolf_killed",
      data: { target_id: "player_5", target_name: "Eve" },
    });
    expect(cast).not.toBeNull();
    expect(cast!.role).toBe("狼人");
    expect(cast!.effectType).toBe("bite");
    expect(cast!.targetId).toBe(5);
    expect(cast!.targetName).toBe("Eve");
    expect(cast!.targetVerb).toBe("击杀");
    expect(cast!.casterName).toBe("狼人"); // team kill — no single caster seat
  });

  it("resolves caster + target names from the roster for seer_checked", () => {
    const cast = castFromEvent(
      { event_type: "seer_checked", data: { player_id: "player_2", target_id: "player_5" } },
      PLAYERS,
    );
    expect(cast).not.toBeNull();
    expect(cast!.role).toBe("预言家");
    expect(cast!.effectType).toBe("inspect");
    expect(cast!.casterId).toBe(2);
    expect(cast!.casterName).toBe("Bob");
    expect(cast!.targetId).toBe(5);
    expect(cast!.targetName).toBe("Eve");
    expect(cast!.targetVerb).toBe("查验");
  });

  it("falls back to '<n>号' when the target name is unknown", () => {
    const cast = castFromEvent({
      event_type: "witch_poison_used",
      data: { player_id: "player_4", target_id: "player_6" },
    });
    expect(cast!.role).toBe("女巫");
    expect(cast!.effectType).toBe("poison");
    expect(cast!.targetVerb).toBe("毒杀");
    expect(cast!.targetName).toBe("6号");
  });

  it("maps guard_protected to a protect cast", () => {
    const cast = castFromEvent(
      { event_type: "guard_protected", data: { player_id: "player_1", target_id: "player_2" } },
      PLAYERS,
    );
    expect(cast!.role).toBe("守卫");
    expect(cast!.targetVerb).toBe("守护");
    expect(cast!.targetName).toBe("Bob");
  });

  it("still builds a 身份揭示 cast from role_revealed (no target)", () => {
    const cast = castFromEvent({
      event_type: "role_revealed",
      data: { player_id: "player_3", player_name: "P3", role: "猎人" },
    });
    expect(cast!.skillName).toBe("身份揭示");
    expect(cast!.targetId).toBeNull();
    expect(cast!.targetVerb).toBe("");
  });

  it("no longer triggers on role_acting (the card is result-event driven now)", () => {
    expect(
      castFromEvent({ event_type: "role_acting", data: { player_id: "player_3", role: "预言家" } }),
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
