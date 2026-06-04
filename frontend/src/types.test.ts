import { describe, expect, it } from "vitest";
import {
  GamePhase,
  PlayState,
  PHASE_LABELS,
  SUB_PHASE_LABELS,
  type GameStateResponse,
  type StreamEvent,
} from "./types";

describe("engine-driven contract types", () => {
  it("GamePhase has the 6 authoritative members", () => {
    expect(Object.values(GamePhase)).toEqual([
      "setup", "night", "sheriff_election", "day_discussion", "day_voting", "ended",
    ]);
  });

  it("PlayState matches /control play_state", () => {
    expect(Object.values(PlayState)).toEqual(["playing", "paused"]);
  });

  it("every phase and key sub-phase has a Chinese label", () => {
    expect(PHASE_LABELS[GamePhase.night]).toBe("黑夜");
    expect(PHASE_LABELS[GamePhase.day_discussion]).toBe("白天讨论");
    expect(SUB_PHASE_LABELS.werewolf_chat).toBe("狼人夜聊中");
    expect(SUB_PHASE_LABELS.witch_decide).toBe("女巫决策中");
    expect(SUB_PHASE_LABELS.seer_check).toBe("预言家查验中");
  });

  it("GameStateResponse / StreamEvent expose the spec fields", () => {
    const state: GameStateResponse = {
      status: "running", error: null, play_state: "playing", speed: 1,
      phase: GamePhase.night, sub_phase: "werewolf_chat", round: 2,
      current_actor_seat: 5, winner: null, sheriff_seat: 3,
      alive_count: 6, dead_count: 2,
      last_night: { deaths: [{ seat: 7, cause: "wolf_kill" }], saved_seat: null, guarded_seat: 4, poisoned_seat: null },
      votes: { by_seat: { "1": 5 }, tally: { "5": 1 } },
      cursor: 142,
      players: [{ seat: 1, name: "A", role: "Seer", camp: "villager", is_alive: true, is_sheriff: false, model: "deepseek-chat", status_flags: ["alive"] }],
    };
    const ev: StreamEvent = {
      seq: 143, type: "skill", phase: GamePhase.night, sub_phase: "werewolf_chat", round: 2,
      reveal: "now", visibility: "wolf",
      skill: { kind: "wolf_kill", actor: { seat: 1 }, target: { seat: 7 }, result: null },
    };
    expect(state.last_night?.deaths[0].seat).toBe(7);
    expect(ev.skill?.kind).toBe("wolf_kill");
  });
});
