import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "./client";

describe("ApiClient.startGame", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  it("POSTs to /games/start with JSON body and unwraps the envelope", async () => {
    const data = {
      run_id: "r1", source: "runs", status: "running", config_id: "standard-6p",
      run_dir: "x", game_page_path: "/game?run_id=r1&source=runs",
      status_path: "/api/v1/games/r1/status", replay_page_path: "/replay/r1",
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ success: true, data, message: null }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await ApiClient.startGame({ config_id: "standard-6p", badge_flow: true });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/games/start");
    expect(opts.method).toBe("POST");
    expect(opts.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(opts.body)).toMatchObject({ config_id: "standard-6p", badge_flow: true });
    expect(res.game_page_path).toBe("/game?run_id=r1&source=runs");
  });

  it("throws with the backend detail on error", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false, statusText: "Bad Request", json: async () => ({ detail: "Unknown config_id: nope" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(ApiClient.startGame({ config_id: "nope" })).rejects.toThrow(/Unknown config_id/);
  });
});
