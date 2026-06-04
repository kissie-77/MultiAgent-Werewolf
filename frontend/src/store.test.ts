import { beforeEach, describe, expect, it, vi } from "vitest";
import { useGameStore } from "./store";
import { MockEventSource } from "./test/MockEventSource";
import { GamePhase } from "./types";

function resetStore() {
  useGameStore.getState().exitToSetup();
  useGameStore.setState({ runId: "r1" });
}

beforeEach(() => {
  resetStore();
  MockEventSource.reset();
});

describe("store SSE transport", () => {
  it("appends a RenderLog when a speech event arrives on the stream", () => {
    useGameStore.getState()._openStream("r1");
    const es = MockEventSource.latest();
    es.emit(
      {
        seq: 1, type: "speech", phase: "day_discussion", sub_phase: null, round: 2,
        reveal: "now", visibility: "public",
        speaker: { seat: 3, name: "C" }, public_text: "hello", private_thought: "psst",
      },
      { id: "1" },
    );
    const logs = useGameStore.getState().logs;
    expect(logs).toHaveLength(1);
    expect(logs[0].kind).toBe("speech");
    expect(logs[0].speakerSeat).toBe(3);
    expect(logs[0].text).toBe("hello");
    expect(useGameStore.getState().cursor).toBe(1);
  });

  it("game-over is driven solely by gameState.phase === 'ended'", async () => {
    const state = {
      status: "ended", error: null, play_state: "paused", speed: 1,
      phase: "ended", sub_phase: null, round: 4, current_actor_seat: null,
      winner: "good", sheriff_seat: null, alive_count: 3, dead_count: 3,
      last_night: null, votes: null, cursor: 99, players: [],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => state }));
    await useGameStore.getState()._refreshState();
    expect(useGameStore.getState().gameState?.phase).toBe(GamePhase.ended);
    expect(useGameStore.getState().isGameOver()).toBe(true);
  });

  it("controlGame('pause') POSTs the action and reflects play_state", async () => {
    const resp = { run_id: "r1", play_state: "paused", speed: 1, phase: "night" };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => resp });
    vi.stubGlobal("fetch", fetchMock);
    await useGameStore.getState().controlGame("pause");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/games/r1/control",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ action: "pause" }) }),
    );
    expect(useGameStore.getState().playState).toBe("paused");
  });
});
