import { describe, it, expect } from "vitest";
import { hydrateStateFromLogEvents, logEventToSse } from "./spectateLog";

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
});
