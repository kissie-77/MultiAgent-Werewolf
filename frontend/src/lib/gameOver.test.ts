import { describe, it, expect } from "vitest";
import {
  clientMvp,
  resolveMvpView,
  resolveBoard,
  resolveWinnerIsGood,
  isWolfRole,
} from "./gameOver";
import type { GameState, Player } from "../types";
import { initialLiveCue } from "./liveCue";
import type { ReplayPageData } from "../api/types";

function player(p: Partial<Player>): Player {
  return {
    id: 0, name: "", role: "村民", isUser: false, isAlive: true,
    avatarSeed: "", lastSpeech: "", statusNotes: "", ...p,
  };
}

function gs(p: Partial<GameState>): GameState {
  return {
    players: [], dayNumber: 1, phase: "GAME_OVER", currentSpeakerId: null, countdown: 0,
    speechLogs: [], eventLog: [], liveCue: initialLiveCue(), narration: "", winner: null, wolfKilledTarget: null, witchSaved: false,
    witchPoisonedTarget: null, seerVerifiedTarget: null, seerVerificationResult: null,
    victimId: null, discussionIndex: 0, executionId: null, ...p,
  };
}

// Minimal backend replay with a villager-2 MVP and a wolf-5 (the bug case).
const backend = {
  run: { winner_camp: "VILLAGERS" },
  mvp_ranking: [
    { rank: 1, playerId: 2, playerName: "Player2", role: "Villager", score: 78.9, isMvp: true },
    { rank: 2, playerId: 5, playerName: "Player5", role: "Werewolf", score: 40, isMvp: false },
  ],
  scores: [
    { playerId: 2, playerName: "Player2", role: "Villager", isAlive: true, totalScore: 78.9 },
    { playerId: 5, playerName: "Player5", role: "Werewolf", isAlive: false, totalScore: 40 },
  ],
} as unknown as ReplayPageData;

describe("clientMvp (BUG-1 crash guard)", () => {
  it("returns null (never undefined) for an empty roster — the seat SSE path", () => {
    expect(clientMvp(gs({ players: [] }))).toBeNull();
    expect(clientMvp(null)).toBeNull();
    expect(clientMvp(undefined)).toBeNull();
  });

  it("picks a player when the roster is populated (local game)", () => {
    const mvp = clientMvp(gs({ players: [player({ id: 1, role: "预言家", isAlive: true })], winner: "VILLAGERS" }));
    expect(mvp?.id).toBe(1);
  });
});

describe("resolveMvpView", () => {
  it("never throws and returns null when there is no backend and no roster", () => {
    expect(resolveMvpView(null, gs({ players: [] }), 1)).toBeNull();
    expect(resolveMvpView(undefined, null, null)).toBeNull();
  });

  it("prefers the backend MVP over the client heuristic (BUG-7)", () => {
    // client heuristic would wrongly favor the surviving wolf-ish player; backend says Player2.
    const clientGs = gs({
      players: [player({ id: 5, role: "Werewolf", isAlive: true })],
      winner: "VILLAGERS",
    });
    const mvp = resolveMvpView(backend, clientGs, 1);
    expect(mvp?.id).toBe(2);
    expect(mvp?.name).toBe("Player2");
    expect(mvp?.role).toBe("Villager");
    expect(mvp?.isAlive).toBe(true);
  });

  it("marks isUser when the MVP is the human seat", () => {
    expect(resolveMvpView(backend, gs({}), 2)?.isUser).toBe(true);
    expect(resolveMvpView(backend, gs({}), 1)?.isUser).toBe(false);
  });

  it("falls back to the client MVP when backend ranking is empty", () => {
    const mvp = resolveMvpView({ mvp_ranking: [], scores: [] } as unknown as ReplayPageData,
      gs({ players: [player({ id: 3, role: "女巫", isAlive: true })], winner: "VILLAGERS" }), 3);
    expect(mvp?.id).toBe(3);
  });
});

describe("resolveBoard", () => {
  it("uses the backend scores when present (seat path has no client roster)", () => {
    const board = resolveBoard(backend, [], 2);
    expect(board.map((b) => b.id)).toEqual([2, 5]);
    expect(board.find((b) => b.id === 2)?.isUser).toBe(true);
    expect(board.find((b) => b.id === 5)?.isAlive).toBe(false);
  });

  it("falls back to the client roster, then to empty", () => {
    expect(resolveBoard(null, [player({ id: 1 })], null).map((b) => b.id)).toEqual([1]);
    expect(resolveBoard(null, [], null)).toEqual([]);
    expect(resolveBoard(null, null, null)).toEqual([]);
  });
});

describe("resolveWinnerIsGood", () => {
  it("prefers backend winner_camp", () => {
    expect(resolveWinnerIsGood(backend, gs({ winner: "WOLVES" }))).toBe(true);
    expect(resolveWinnerIsGood({ run: { winner_camp: "WOLVES" } } as ReplayPageData, gs({ winner: "VILLAGERS" }))).toBe(false);
  });
  it("falls back to client winner", () => {
    expect(resolveWinnerIsGood(null, gs({ winner: "VILLAGERS" }))).toBe(true);
    expect(resolveWinnerIsGood(null, gs({ winner: "WOLVES" }))).toBe(false);
  });
});

describe("isWolfRole", () => {
  it("matches both Chinese and English wolf roles", () => {
    expect(isWolfRole("狼人")).toBe(true);
    expect(isWolfRole("Werewolf")).toBe(true);
    expect(isWolfRole("村民")).toBe(false);
    expect(isWolfRole("Villager")).toBe(false);
  });
});
