import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "./client";

describe("ApiClient.getReplayData", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  function backendPage() {
    return {
      run: {
        run_id: "run1",
        source: "runs",
        path: "/x",
        created_at: "2026-06-06T12:00:00",
        player_count: 6,
        winner_camp: "werewolf",
        has_post_game: true,
        has_replay: true,
        roster: [],
      },
      timeline: [
        { index: 0, event_type: "player_speech", round_number: 1, phase: "day_discussion", message: "hi", data: { player_id: "player_1", speech: "hi" } },
        { index: 1, event_type: "belief_snapshot", round_number: 1, phase: "day_discussion", message: "belief", data: {} },
      ],
      turning_points: ["首日放逐狼人"],
      mvp_ranking: [
        { rank: 1, player_id: "player_5", player_name: "Player5", role_name: "Witch", total_score: 0.0 },
      ],
      scores: [],
      report_markdown: "# R",
      coach_excerpt: null,
    };
  }

  it("requests run_id, source=runs and view=god, then maps through mapReplayPage", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: backendPage(), message: null }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await ApiClient.getReplayData("run1");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0];
    const u = String(url);
    expect(u).toContain("/api/v1/pages/replay");
    expect(u).toContain("run_id=run1");
    expect(u).toContain("source=runs");
    expect(u).toContain("view=god");

    // mapped: winner_camp normalised, god-injected belief event filtered out
    expect(res.run.winner_camp).toBe("WOLVES");
    expect(res.timeline).toHaveLength(1);
    expect(res.timeline[0].id).toBe("0");
    expect(res.mvp_ranking[0].isMvp).toBe(true);
    expect(res.mvp_ranking[0].playerId).toBe(5);
    expect(res.turning_points[0].title).toBe("首日放逐狼人");
    expect(res.coach_excerpt).toBe("");
  });
});
