import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchState, postControl, streamUrl, isNightPhase } from "./api";
import { GamePhase } from "../types";

afterEach(() => vi.restoreAllMocks());

describe("api helpers", () => {
  it("streamUrl points at the SSE endpoint", () => {
    expect(streamUrl("r1")).toBe("/api/v1/games/r1/stream");
  });

  it("isNightPhase is true only for night/setup", () => {
    expect(isNightPhase(GamePhase.night)).toBe(true);
    expect(isNightPhase(GamePhase.setup)).toBe(true);
    expect(isNightPhase(GamePhase.day_discussion)).toBe(false);
    expect(isNightPhase(GamePhase.day_voting)).toBe(false);
    expect(isNightPhase(GamePhase.ended)).toBe(false);
  });

  it("fetchState GETs /state and unwraps the body", async () => {
    const body = { phase: "night", round: 1 };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => body });
    vi.stubGlobal("fetch", fetchMock);
    const state = await fetchState("r1");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/games/r1/state");
    expect(state.phase).toBe("night");
  });

  it("postControl POSTs the action body and returns the response", async () => {
    const resp = { run_id: "r1", play_state: "paused", speed: 2, phase: "night" };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => resp });
    vi.stubGlobal("fetch", fetchMock);
    const out = await postControl("r1", { action: "speed", value: 2 });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/games/r1/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "speed", value: 2 }),
    });
    expect(out.play_state).toBe("paused");
  });
});
