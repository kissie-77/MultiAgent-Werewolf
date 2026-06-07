import { describe, it, expect } from "vitest";
import { mapHomePage, type BackendHomePageData } from "./homeMap";

// The real backend GET /api/v1/pages/home payload shape (snake_case).
const raw: BackendHomePageData = {
  hero: { title: "AI 狼人杀", subtitle: "多智能体狼人杀博弈平台", cta_label: "开始对局", cta_path: "/game" },
  stats_cards: [
    { label: "历史对局", value: 26, unit: "局", hint: null },
    { label: "角色数量", value: 22, unit: "个", hint: null },
    { label: "可用配置", value: 12, unit: "套", hint: null },
    { label: "含复盘", value: 26, unit: "局", hint: null },
  ],
  recent_runs: [
    { run_id: "6p-deepseek-1", created_at: "2026-06-07T14:57:09", player_count: 6, winner_camp: "werewolf", has_replay: true },
    { run_id: "12p-deepseek-2", created_at: "2026-06-07T13:00:00", player_count: 12, winner_camp: "villager", has_replay: false },
  ],
  quick_actions: [{ key: "game", title: "开始对局", path: "/game", description: "主游戏页" }],
};

describe("mapHomePage", () => {
  it("maps hero into title/subtitle/description", () => {
    const out = mapHomePage(raw);
    expect(out.title).toBe("AI 狼人杀");
    expect(out.subtitle).toBe("多智能体狼人杀博弈平台");
    expect(out.description).toBe("多智能体狼人杀博弈平台");
  });

  it("always returns a defined stats object (the white-screen regression)", () => {
    const out = mapHomePage(raw);
    // HomePage reads data.stats.activeGames — stats must never be undefined.
    expect(out.stats).toBeDefined();
    expect(typeof out.stats.activeGames).toBe("number");
    expect(out.stats.totalMatchesPlayed).toBe(26); // label "历史对局"
    expect(typeof out.stats.averageRating).toBe("string");
  });

  it("maps recent_runs into highlights with camp labels", () => {
    const out = mapHomePage(raw);
    expect(out.highlights).toHaveLength(2);
    expect(out.highlights[0].id).toBe("6p-deepseek-1");
    expect(out.highlights[0].category).toBe("狼人胜");
    expect(out.highlights[1].category).toBe("好人胜");
    expect(out.highlights[0].date).toBe("2026-06-07T14:57:09");
  });

  it("is null-safe: empty payload never throws and stats stays defined", () => {
    for (const bad of [null, undefined, {}, { hero: null, stats_cards: null, recent_runs: null }]) {
      const out = mapHomePage(bad as BackendHomePageData);
      expect(out.stats).toBeDefined();
      expect(out.stats.activeGames).toBe(0);
      expect(Array.isArray(out.highlights)).toBe(true);
      expect(out.title).toBeTruthy(); // falls back to a default title
    }
  });
});
