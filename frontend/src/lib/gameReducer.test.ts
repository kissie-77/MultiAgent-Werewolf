import { describe, it, expect } from "vitest";
import { initialSpectateState, reduceEvent } from "./gameReducer";

const snapshot = {
  event_type: "snapshot",
  phase: "night",
  round_number: 1,
  roster: [
    { seat: 1, name: "P1", role: "Seer", camp: "villager", is_alive: true },
    { seat: 2, name: "P2", role: "Werewolf", camp: "werewolf", is_alive: true },
  ],
};

describe("gameReducer", () => {
  it("builds players + phase from a god snapshot", () => {
    const s = reduceEvent(initialSpectateState(), snapshot as any);
    expect(s.players.map((p) => p.id)).toEqual([1, 2]);
    expect(s.players[0].role).toBe("Seer");
    expect(s.phase).toBe("NIGHT_WOLF");
    expect(s.dayNumber).toBe(1);
  });

  it("appends speech and sets current speaker", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_speech", round_number: 2, phase: "day_discussion",
      message: "我是预言家", data: { player_id: "player_1", reasoning: "因为..." },
    } as any);
    expect(s.phase).toBe("DAY_DEBATE");
    expect(s.currentSpeakerId).toBe(1);
    expect(s.speechLogs.at(-1)).toMatchObject({ playerId: 1, content: "我是预言家" });
  });

  it("marks a player dead on player_died", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_died", round_number: 2, phase: "night",
      message: "P2 倒下", data: { player_id: "player_2" },
    } as any);
    expect(s.players.find((p) => p.id === 2)!.isAlive).toBe(false);
  });

  it("prefers data.speech over formatted message for speech logs", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_speech", round_number: 2, phase: "day_discussion",
      message: "Player1: 我是预言家", data: { player_id: "player_1", speech: "我是预言家" },
    } as any);
    expect(s.speechLogs.at(-1)?.content).toBe("我是预言家");
  });

  it("builds players from role_acting when snapshot is absent", () => {
    const s = reduceEvent(initialSpectateState(), {
      event_type: "role_acting", round_number: 1, phase: "night",
      data: { player_id: "player_3", player_name: "C", role: "Witch" },
    } as any);
    expect(s.players).toHaveLength(1);
    expect(s.players[0]).toMatchObject({ id: 3, role: "Witch", name: "C" });
  });

  it("ends the game on game_ended", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "game_ended", round_number: 3, phase: "ended",
      message: "狼人胜", data: { winner_camp: "werewolf" },
    } as any);
    expect(s.phase).toBe("GAME_OVER");
    expect(s.winner).toBe("WOLVES");
  });
});
