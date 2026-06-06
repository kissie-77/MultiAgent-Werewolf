import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "./client";

describe("ApiClient.getGameStatus", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  it("GETs /games/{runId}/status?source=runs and unwraps the envelope", async () => {
    const data = {
      run_id: "run1",
      source: "runs",
      status: "ended",
      snapshot: {
        phase: "GAME_OVER",
        round_number: 3,
        winner_camp: "villager",
        is_ended: true,
        sheriff_id: null,
        alive_count: 4,
        dead_count: 2,
        event_count: 42,
      },
      error: null,
      result_text: "好人胜利",
      has_post_game: true,
      has_replay: true,
      post_game_status: "ok",
      alert_count: 0,
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data, message: null }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await ApiClient.getGameStatus("run1");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/games/run1/status?source=runs");
    expect(res.has_post_game).toBe(true);
    expect(res.snapshot?.winner_camp).toBe("villager");
  });

  it("honors a custom source argument", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        data: { run_id: "r2", source: "eval", status: "running", has_post_game: false },
        message: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await ApiClient.getGameStatus("r2", "eval");

    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/games/r2/status?source=eval");
    expect(res.has_post_game).toBe(false);
  });

  it("encodes the runId path segment", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: { run_id: "a/b", has_post_game: false }, message: null }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await ApiClient.getGameStatus("a/b");

    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/games/a%2Fb/status?source=runs");
  });
});
