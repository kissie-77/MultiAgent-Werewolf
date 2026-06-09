import { describe, it, expect } from "vitest";
import {
  effectTypeSfx, eventSfx, stageSfx, sfxPath,
  createBurstGate, createEventDedup,
  bgmIdForPhase, BGM_IDS, ALL_SFX_IDS,
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

describe("bgmIdForPhase", () => {
  it("maps night phases to the night loop", () => {
    expect(bgmIdForPhase("NIGHT_WOLF")).toBe("bgm_night");
    expect(bgmIdForPhase("NIGHT_SEER")).toBe("bgm_night");
    expect(bgmIdForPhase("NIGHT_WITCH")).toBe("bgm_night");
  });
  it("maps voting phases to the tension loop", () => {
    expect(bgmIdForPhase("DAY_VOTE")).toBe("bgm_tension");
    expect(bgmIdForPhase("DAY_SHERIFF_VOTE")).toBe("bgm_tension");
  });
  it("maps daytime talk phases to the day ambience", () => {
    expect(bgmIdForPhase("DAY_SHERIFF_RUN")).toBe("bgm_day");
    expect(bgmIdForPhase("DAY_ANNOUNCEMENT")).toBe("bgm_day");
    expect(bgmIdForPhase("DAY_DEBATE")).toBe("bgm_day");
  });
  it("maps game over to the settlement track", () => {
    expect(bgmIdForPhase("GAME_OVER")).toBe("bgm_settlement");
  });
  it("falls back to the lobby track for lobby phases and null (off-game pages)", () => {
    expect(bgmIdForPhase("START_SCREEN")).toBe("bgm_lobby");
    expect(bgmIdForPhase("ROLE_CHOICE")).toBe("bgm_lobby");
    expect(bgmIdForPhase(null)).toBe("bgm_lobby");
    expect(bgmIdForPhase(undefined)).toBe("bgm_lobby");
  });
  it("only ever returns ids present in BGM_IDS", () => {
    const phases = ["NIGHT_WOLF", "DAY_VOTE", "DAY_DEBATE", "GAME_OVER", "START_SCREEN", null, undefined, "??"];
    for (const p of phases) expect(BGM_IDS).toContain(bgmIdForPhase(p));
  });
  it("keeps BGM out of the SFX preload list (large files load lazily)", () => {
    for (const id of BGM_IDS) expect(ALL_SFX_IDS).not.toContain(id);
  });
});
