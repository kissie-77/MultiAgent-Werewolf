import { describe, it, expect } from "vitest";
import { isPostGameReady, replayPathFor } from "./settlement";
import type { GameStatusResponse } from "../api/types";

function status(overrides: Partial<GameStatusResponse>): GameStatusResponse {
  return {
    run_id: "run1",
    source: "runs",
    status: "ended",
    snapshot: null,
    error: null,
    result_text: null,
    has_post_game: false,
    has_replay: false,
    post_game_status: null,
    alert_count: null,
    ...overrides,
  };
}

describe("settlement", () => {
  it("isPostGameReady is true only when has_post_game === true", () => {
    expect(isPostGameReady(status({ has_post_game: true }))).toBe(true);
    expect(isPostGameReady(status({ has_post_game: false }))).toBe(false);
  });

  it("isPostGameReady tolerates null/undefined input", () => {
    expect(isPostGameReady(null)).toBe(false);
    expect(isPostGameReady(undefined)).toBe(false);
  });

  it("isPostGameReady does not treat truthy non-boolean as ready", () => {
    // defensive: a string "true" must not pass the strict === true gate
    expect(isPostGameReady({ has_post_game: "true" } as unknown as GameStatusResponse)).toBe(false);
  });

  it("replayPathFor builds /replay/{runId}", () => {
    expect(replayPathFor("run1")).toBe("/replay/run1");
    expect(replayPathFor("abc-123")).toBe("/replay/abc-123");
  });
});
