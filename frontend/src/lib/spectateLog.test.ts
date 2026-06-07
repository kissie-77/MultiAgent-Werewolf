import { describe, it, expect, vi } from "vitest";
import {
  delayForLogEvent,
  hydrateStateFromLogEvents,
  initialStateWithRoster,
  logEventToSse,
  startLogReplayDrain,
} from "./spectateLog";

describe("spectateLog", () => {
  it("maps replay rows into reducer events", () => {
    const sse = logEventToSse({
      index: 1,
      event_type: "player_speech",
      round_number: 1,
      phase: "day_discussion",
      message: "x",
      data: { player_id: "player_2", speech: "hello" },
    });
    expect(sse.event_type).toBe("player_speech");
    expect(sse.data?.speech).toBe("hello");
  });

  it("hydrates speech logs from a full timeline", () => {
    const state = hydrateStateFromLogEvents(
      [
        {
          index: 1,
          event_type: "role_acting",
          round_number: 1,
          phase: "night",
          message: "",
          data: { player_id: "player_1", player_name: "A", role: "Seer" },
        },
        {
          index: 2,
          event_type: "player_speech",
          round_number: 1,
          phase: "day_discussion",
          message: "A: hi",
          data: { player_id: "player_1", speech: "hi" },
        },
      ],
      [{ seat: 1, name: "A", role: "Seer", camp: "villager", is_alive: true }],
    );
    expect(state.speechLogs).toHaveLength(1);
    expect(state.speechLogs[0].content).toBe("hi");
  });

  it("seeds roster before streaming events", () => {
    const seed = initialStateWithRoster([
      { seat: 1, name: "A", role: "Seer", camp: "villager", is_alive: true },
    ]);
    expect(seed.players).toHaveLength(1);
    expect(seed.players[0].name).toBe("A");
  });

  it("uses longer delay for speech events", () => {
    expect(delayForLogEvent({ index: 1, event_type: "player_speech", round_number: 1, phase: "day_discussion", message: "", data: {} })).toBeGreaterThan(
      delayForLogEvent({ index: 2, event_type: "phase_changed", round_number: 1, phase: "day_discussion", message: "", data: {} }),
    );
  });

  it("drains events stepwise and updates insight snapshots", () => {
    vi.useFakeTimers();
    const steps: string[] = [];
    const roster = [{ seat: 1, name: "A", role: "Seer", camp: "villager", is_alive: true }];
    const { stop } = startLogReplayDrain({
      events: [
        {
          index: 1,
          event_type: "player_speech",
          round_number: 1,
          phase: "day_discussion",
          message: "",
          data: { player_id: "player_1", speech: "hi" },
        },
        {
          index: 2,
          event_type: "belief_snapshot",
          round_number: 1,
          phase: "day_discussion",
          message: "",
          data: { round: 1, beliefs: [] },
        },
      ],
      initial: initialStateWithRoster(roster),
      isPaused: () => false,
      mapBelief: () => [{
        round: 1,
        phase: "day_discussion",
        anchor: "test",
        observer_id: "player_1",
        observer_seat: 1,
        vote_intention: { seat: 1, reason: "" },
        first_order: [],
      }],
      mapVote: () => null,
      onStep: (state, insight) => {
        steps.push(insight?.beliefs ? "belief" : `speech:${state.speechLogs.length}`);
      },
      onComplete: () => steps.push("done"),
    });

    vi.runAllTimers();
    stop();
    vi.useRealTimers();

    expect(steps).toContain("speech:1");
    expect(steps).toContain("belief");
    expect(steps[steps.length - 1]).toBe("done");
  });
});
