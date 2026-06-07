import { describe, expect, it } from "vitest";
import { isPostGameFailed, isPostGameReady } from "./settlement";

describe("settlement helpers", () => {
  it("isPostGameReady requires has_post_game", () => {
    expect(isPostGameReady({ has_post_game: true } as any)).toBe(true);
    expect(isPostGameReady({ has_post_game: false } as any)).toBe(false);
  });

  it("isPostGameFailed detects failed pipeline status", () => {
    expect(
      isPostGameFailed({ status: "post_game_failed", has_post_game: false } as any),
    ).toBe(true);
    expect(
      isPostGameFailed({ status: "completed", post_game_status: "failed" } as any),
    ).toBe(true);
    expect(
      isPostGameFailed({ status: "completed", post_game_status: "ok", has_post_game: true } as any),
    ).toBe(false);
  });
});
