import { describe, expect, it } from "vitest";
import { mapHomePage } from "./homeMap";
import type { BackendHomePageData } from "../api/types";

const raw: BackendHomePageData = {
  hero: {
    title: "AI 狼人杀",
    subtitle: "观看 AI 对局、复盘分析、对比模型表现。",
    cta_label: "开始对局",
    cta_path: "/game",
  },
  stats_cards: [
    { label: "历史对局", value: 62, unit: "局" },
    { label: "角色数量", value: 22, unit: "个" },
    { label: "可用配置", value: 13, unit: "套" },
    { label: "含复盘", value: 57, unit: "局" },
  ],
  recent_runs: [
    {
      run_id: "6p-deepseek-20260606-235251",
      source: "runs",
      path: "/runs/1",
      created_at: "2026-06-06T23:59:41",
      player_count: 6,
      winner_camp: "werewolf",
      has_post_game: true,
      has_replay: true,
    },
    {
      run_id: "6p-deepseek-20260607-001513",
      source: "runs",
      path: "/runs/2",
      created_at: "2026-06-07T00:22:02",
      player_count: 6,
      winner_camp: null,
      has_post_game: false,
      has_replay: true,
    },
  ],
  quick_actions: [
    { key: "game", title: "开始对局", path: "/game", description: "主游戏页" },
  ],
};

describe("mapHomePage", () => {
  it("maps the backend home payload into the page's expected shape", () => {
    const out = mapHomePage(raw);
    expect(out.title).toBe("AI 狼人杀");
    expect(out.description).toContain("复盘分析");
    expect(out.stats.totalMatchesPlayed).toBe(62);
    expect(out.stats.onlineAIs).toBe(13);
    expect(out.stats.averageRating).toBe("57");
    expect(out.stats.activeGames).toBe(1);
  });

  it("maps recent runs into dashboard highlights", () => {
    const out = mapHomePage(raw);
    expect(out.highlights).toHaveLength(2);
    expect(out.highlights[0].title).toBe("狼人胜");
    expect(out.highlights[0].category).toBe("6人局");
    expect(out.highlights[0].date).toBe("2026-06-06 23:59");
  });

  it("is defensive against missing fields", () => {
    const out = mapHomePage({});
    expect(out.title).toBeTruthy();
    expect(out.stats.activeGames).toBe(0);
    expect(out.highlights).toEqual([]);
    expect(out.quickLinks).toEqual([]);
  });
});
