import { describe, it, expect } from "vitest";
import { mapSharePage } from "./shareMap";
import type { BackendShareReplayData } from "../api/types";

const raw: BackendShareReplayData = {
  run_id: "6p-deepseek-20260606-141224",
  share_title: "AI 狼人杀复盘 · 6p",
  share_summary: "6 人局 · 胜方：villager",
  winner_camp: "villager",
  mvp_winner: {
    rank: 1,
    player_id: "player_5",
    player_name: "Player5",
    role_name: "Seer",
    total_score: 0.0,
    ai_model: "deepseek-chat",
  },
  key_moments: ["第2天放逐了4号狼人", "女巫毒杀关键发言者"],
  highlight_players: [],
  stats_line: "6 人 · 胜方 villager · MVP Player5",
};

describe("mapSharePage", () => {
  it("camelCases mvp_winner fields the SharePage reads", () => {
    const out = mapSharePage(raw);
    expect(out.mvp_winner.playerName).toBe("Player5");
    expect(out.mvp_winner.role).toBe("Seer");
    expect(out.mvp_winner.playerId).toBe(5);
  });

  it("supplies a non-empty mvp citation fallback (backend has none)", () => {
    expect(mapSharePage(raw).mvp_winner.citation.length).toBeGreaterThan(0);
  });

  it("normalizes winner_camp to the WOLVES/VILLAGERS enum", () => {
    expect(mapSharePage(raw).winner_camp).toBe("VILLAGERS");
    expect(mapSharePage({ ...raw, winner_camp: "werewolf" }).winner_camp).toBe("WOLVES");
  });

  it("carries title / summary / stats_line through", () => {
    const out = mapSharePage(raw);
    expect(out.share_title).toBe(raw.share_title);
    expect(out.share_summary).toBe(raw.share_summary);
    expect(out.stats_line).toBe(raw.stats_line);
  });

  it("is defensive against a missing mvp_winner", () => {
    const out = mapSharePage({ ...raw, mvp_winner: null });
    expect(out.mvp_winner.playerName).toBe("");
    expect(out.mvp_winner.citation.length).toBeGreaterThan(0);
  });

  it("is defensive against null input", () => {
    const out = mapSharePage(null as unknown as BackendShareReplayData);
    expect(out.winner_camp).toBe("VILLAGERS");
    expect(out.mvp_winner.playerName).toBe("");
  });
});
