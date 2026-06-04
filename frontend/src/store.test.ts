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
    // REAL backend wire shape (models/view.py ViewEvent, spec §5.2): the event
    // carries `round` (NOT `day`) and has no top-level `sub_phase` field.
    es.emit(
      {
        seq: 1, type: "speech", phase: "day_discussion", round: 2,
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
    // Contract guard: `round` from the backend-shaped event reaches the RenderLog
    // (drives the "ROUND {n}" badge in SpeechConsole). Was broken when the wire
    // key was `day` but the frontend read `ev.round`.
    expect(logs[0].round).toBe(2);
    expect(useGameStore.getState().cursor).toBe(1);
  });

  it("renders the sub_phase name from a backend-shaped sub_phase event (top-level `name`)", () => {
    useGameStore.getState()._openStream("r1");
    const es = MockEventSource.latest();
    // REAL backend wire shape: a sub_phase-type event delivers its display-hint
    // text at the TOP LEVEL as `name` (NOT nested under `sub_phase`). Was broken
    // when the backend emitted `sub_phase: {name}` but the frontend read `ev.name`.
    es.emit(
      {
        seq: 2, type: "sub_phase", phase: "night", round: 1,
        reveal: "now", visibility: "public", name: "werewolf_chat",
      },
      { id: "2" },
    );
    const logs = useGameStore.getState().logs;
    expect(logs).toHaveLength(1);
    expect(logs[0].kind).toBe("sub_phase");
    expect(logs[0].text).toBe("werewolf_chat");
    expect(logs[0].round).toBe(1);
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

  it("stepGame() flushes queued events to logs even though step auto-pauses", async () => {
    // Start paused, with the stepped phase's events already buffered in the queue
    // (the common case: SSE frames arrive before the await postControl resolves).
    useGameStore.setState({ playState: "paused" });
    useGameStore.getState()._openStream("r1");
    const es = MockEventSource.latest();
    es.emit(
      {
        seq: 5, type: "speech", phase: "night", round: 1,
        reveal: "now", visibility: "wolf",
        speaker: { seat: 1, name: "A" }, public_text: "kill 2", private_thought: null,
      },
      { id: "5" },
    );
    // While paused, the SSE listener must NOT have flushed it yet.
    expect(useGameStore.getState().logs).toHaveLength(0);
    expect(useGameStore.getState().queue).toHaveLength(1);

    // step auto-pauses (spec §5.3): POST returns play_state: "paused".
    const resp = { run_id: "r1", play_state: "paused", speed: 1, phase: "night" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => resp }));
    await useGameStore.getState().stepGame();

    // The stepped phase's event must now be rendered into logs.
    expect(useGameStore.getState().playState).toBe("paused");
    expect(useGameStore.getState().logs).toHaveLength(1);
    expect(useGameStore.getState().logs[0].text).toBe("kill 2");
    expect(useGameStore.getState().queue).toHaveLength(0);
  });

  it("step renders events that arrive AFTER the control POST resolves (no race)", async () => {
    useGameStore.setState({ playState: "paused" });
    useGameStore.getState()._openStream("r1");
    const es = MockEventSource.latest();

    const resp = { run_id: "r1", play_state: "paused", speed: 1, phase: "night" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => resp }));
    await useGameStore.getState().stepGame();
    expect(useGameStore.getState().playState).toBe("paused");

    // Now the stepped phase emits its events (arriving after the POST resolved).
    es.emit(
      {
        seq: 9, type: "vote", phase: "day_voting", round: 2,
        reveal: "now", visibility: "public",
        vote: { voter: { seat: 3 }, target: { seat: 6 } },
      },
      { id: "9" },
    );
    const logs = useGameStore.getState().logs;
    expect(logs).toHaveLength(1);
    expect(logs[0].kind).toBe("vote");
    expect(useGameStore.getState().queue).toHaveLength(0);
  });

  it("cancelGame() returns to setup (clears gameState so App.inSetup re-triggers)", async () => {
    useGameStore.setState({
      runId: "r1",
      status: "running",
      gameState: { phase: "night" } as never,
      logs: [{ seq: 1 } as never],
    });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);
    await useGameStore.getState().cancelGame();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/games/r1/cancel",
      expect.objectContaining({ method: "POST" }),
    );
    const st = useGameStore.getState();
    expect(st.gameState).toBeNull();
    expect(st.runId).toBeNull();
    expect(st.status).toBe("idle"); // App.inSetup is true on status==='idle' || !gameState
    expect(st.logs).toHaveLength(0);
  });
});
