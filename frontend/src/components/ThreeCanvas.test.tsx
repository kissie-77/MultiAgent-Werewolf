import { describe, expect, it } from "vitest";
import { isNightPhase } from "../lib/api";
import { GamePhase } from "../types";

// ThreeCanvas night logic must come from isNightPhase(gameState.phase),
// never from a literal `phase === "night"` string comparison.
describe("ThreeCanvas night derivation", () => {
  it("matches isNightPhase for every GamePhase", () => {
    expect(isNightPhase(GamePhase.night)).toBe(true);
    expect(isNightPhase(GamePhase.setup)).toBe(true);
    expect(isNightPhase(GamePhase.sheriff_election)).toBe(false);
    expect(isNightPhase(GamePhase.day_discussion)).toBe(false);
    expect(isNightPhase(GamePhase.day_voting)).toBe(false);
    expect(isNightPhase(GamePhase.ended)).toBe(false);
  });
});
