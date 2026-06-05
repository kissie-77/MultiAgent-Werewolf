import { describe, it, expect } from "vitest";
import { mapRunRow } from "./runRows";
import type { RunSummary } from "../api/types";

const base: RunSummary = {
  run_id: "demo-6-20260606-101010",
  source: "runs",
  path: "/x",
  created_at: "06-06",
  player_count: 6,
  winner_camp: "good",
  has_post_game: true,
  has_replay: true,
};

describe("mapRunRow", () => {
  it("normalizes winner_camp to upper-case canonical value", () => {
    expect(mapRunRow(base).winnerCamp).toBe("GOOD");
    expect(mapRunRow({ ...base, winner_camp: "werewolf" }).winnerCamp).toBe("WEREWOLF");
  });

  it("falls back to UNKNOWN for null/unexpected winner_camp", () => {
    expect(mapRunRow({ ...base, winner_camp: null }).winnerCamp).toBe("UNKNOWN");
    expect(mapRunRow({ ...base, winner_camp: "??" }).winnerCamp).toBe("UNKNOWN");
  });

  it("defaults missing player_count/created_at", () => {
    const r = mapRunRow({ ...base, player_count: null, created_at: null });
    expect(r.playerCount).toBe(0);
    expect(r.createdAt).toBe("");
  });

  it("carries run_id and has_replay through", () => {
    const r = mapRunRow(base);
    expect(r.runId).toBe(base.run_id);
    expect(r.hasReplay).toBe(true);
  });
});
