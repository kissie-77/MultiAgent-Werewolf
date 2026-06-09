import { describe, it, expect } from "vitest";
import { buildPreviewSeats } from "./previewSeats";
import type { GameState } from "../types";

const livePlayers: GameState["players"] = [
  { id: 1, name: "A", isAlive: true, isUser: true } as GameState["players"][number],
  { id: 2, name: "B", isAlive: false, isUser: false } as GameState["players"][number],
];

describe("buildPreviewSeats", () => {
  it("undefined phase (landing) + setupCount renders a synthetic ring, seat 1 is the user", () => {
    const seats = buildPreviewSeats({ phase: undefined, setupCount: 6, players: [], currentSpeakerId: null });
    expect(seats).toHaveLength(6);
    expect(seats[0]).toMatchObject({ id: 1, isUser: true, isAlive: true });
    expect(seats[5]).toMatchObject({ id: 6, isUser: false });
  });

  it("START_SCREEN + setupCount honors the chosen player count", () => {
    expect(buildPreviewSeats({ phase: "START_SCREEN", setupCount: 9, players: [], currentSpeakerId: null }))
      .toHaveLength(9);
  });

  it("lobby with no setupCount yet falls back to mapping players (empty -> [])", () => {
    expect(buildPreviewSeats({ phase: undefined, setupCount: null, players: [], currentSpeakerId: null }))
      .toEqual([]);
  });

  it("live phase maps real players and marks the current speaker", () => {
    const seats = buildPreviewSeats({ phase: "DAY_DEBATE", setupCount: 6, players: livePlayers, currentSpeakerId: 1 });
    expect(seats).toHaveLength(2);
    expect(seats[0]).toMatchObject({ id: 1, isSpeaking: true, isAlive: true, isUser: true });
    expect(seats[1]).toMatchObject({ id: 2, isSpeaking: false, isAlive: false });
  });
});
