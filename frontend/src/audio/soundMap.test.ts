import { describe, it, expect } from "vitest";
import {
  effectTypeSfx, eventSfx, stageSfx, sfxPath,
  createBurstGate, createEventDedup,
} from "./soundMap";

describe("effectTypeSfx", () => {
  it("covers new skill effects", () => {
    expect(effectTypeSfx.poison).toBe("skill_poison");
    expect(effectTypeSfx.charm).toBe("skill_charm");
    expect(effectTypeSfx.rally).toBe("skill_vote");
  });
});

describe("eventSfx", () => {
  it("maps public events", () => {
    expect(eventSfx({ event_type: "player_died" })).toBe("event_death_reveal");
    expect(eventSfx({ event_type: "player_eliminated" })).toBe("event_execution");
    expect(eventSfx({ event_type: "vote_result" })).toBe("event_vote_tally");
    expect(eventSfx({ event_type: "sheriff_elected" })).toBe("event_sheriff_elected");
  });
  it("splits game_ended by winner camp", () => {
    expect(eventSfx({ event_type: "game_ended", data: { winner_camp: "villager" } })).toBe("event_victory_good");
    expect(eventSfx({ event_type: "game_ended", data: { winner_camp: "werewolf" } })).toBe("event_victory_evil");
  });
  it("returns null for unmapped", () => {
    expect(eventSfx({ event_type: "actor_thinking" })).toBeNull();
  });
});

describe("stageSfx", () => {
  it("maps night/day only", () => {
    expect(stageSfx("night")).toBe("event_nightfall");
    expect(stageSfx("day")).toBe("event_dawn");
    expect(stageSfx("lobby")).toBeNull();
    expect(stageSfx("over")).toBeNull();
  });
});

describe("sfxPath", () => {
  it("builds public path", () => {
    expect(sfxPath("skill_bite")).toBe("/audio/skill_bite.mp3");
  });
});

describe("createBurstGate", () => {
  it("allows up to max then suppresses within window", () => {
    const g = createBurstGate(700, 3);
    expect(g.allow(0)).toBe(true);
    expect(g.allow(10)).toBe(true);
    expect(g.allow(20)).toBe(true);
    expect(g.allow(30)).toBe(false);
  });
  it("recovers after window passes", () => {
    const g = createBurstGate(700, 3);
    g.allow(0); g.allow(10); g.allow(20);
    expect(g.allow(800)).toBe(true);
  });
});

describe("createEventDedup", () => {
  it("skips already-seen monotonic ids, passes new", () => {
    const d = createEventDedup();
    expect(d.seen(5)).toBe(false);
    expect(d.seen(5)).toBe(true);
    expect(d.seen(4)).toBe(true);
    expect(d.seen(6)).toBe(false);
  });
  it("never dedups when id is undefined", () => {
    const d = createEventDedup();
    expect(d.seen(undefined)).toBe(false);
    expect(d.seen(undefined)).toBe(false);
  });
});
