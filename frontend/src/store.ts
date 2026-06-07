import { create } from "zustand";
import { GameState } from "./types";
import type { AwaitingInputEvent } from "./api/types";
import type { HumanInputSelection } from "./lib/humanInput";
import {
  initialSpectateState,
  reduceEvent,
} from "./lib/gameReducer";
import { streamUrl } from "./api/sse";
import { mapBeliefEvent, mapVoteEvent } from "./lib/insightMap";

/** Monotonic token so stale SSE connect callbacks are ignored after disconnect/switch. */
let sseConnectGen = 0;

interface GameStore {
  state: GameState | null;
  isLoading: boolean;
  setupCount: number | null;
  insightEnabled: boolean;
  setSetupCount: (count: number | null) => void;
  setInsightEnabled: (enabled: boolean) => void;
  exitGame: () => void;

  // Live spectate (SSE god view)
  spectateSource: EventSource | null;
  spectateError: string | null;
  insightBeliefs: import("./api/insightTypes").BeliefSnapshot[] | null;
  insightVote: import("./api/insightTypes").VoteIntentionSnapshot | null;
  spectateRoster: import("./lib/insightMap").RosterEntry[] | null;
  connectSpectate: (runId: string) => void;
  disconnectSpectate: () => void;

  // Human vs AI seat view (SSE seat stream + awaiting_input bridge)
  pendingInput: AwaitingInputEvent | null;
  playerToken: string | null;
  humanSeat: number | null;
  seatRunId: string | null;
  humanInputError: string | null;
  connectSeat: (runId: string, opts: { seat: number; token: string }) => void;
  ingestSeatEvent: (ev: unknown) => boolean;
  submitHumanInput: (selection: HumanInputSelection) => Promise<void>;
  clearPendingInput: () => void;
  clearHumanInputError: () => void;
}

export const useGameStore = create<GameStore>((set, get) => ({
  state: null,
  isLoading: false,
  setupCount: null,
  insightEnabled: true,

  setSetupCount: (count) => set({ setupCount: count }),
  setInsightEnabled: (enabled) => set({ insightEnabled: enabled }),

  exitGame: () => {
    set({ isLoading: false, pendingInput: null, humanInputError: null });
    get().disconnectSpectate();
    window.location.href = "/";
  },

  spectateSource: null,
  spectateError: null,
  insightBeliefs: null,
  insightVote: null,
  spectateRoster: null,

  connectSpectate: (runId) => {
    get().disconnectSpectate();
    const gen = ++sseConnectGen;
    set({
      insightBeliefs: null,
      insightVote: null,
      spectateRoster: null,
      spectateError: null,
      humanInputError: null,
    });
    set({ state: initialSpectateState(), isLoading: false });

    const es = new EventSource(streamUrl(runId, "god"));

    es.addEventListener("snapshot", (e: MessageEvent) => {
      if (gen !== sseConnectGen) return;
      try {
        const snap = JSON.parse(e.data);
        const cur = get().state ?? initialSpectateState();
        set({
          state: reduceEvent(cur, { ...snap, event_type: "snapshot" }),
          spectateRoster: Array.isArray(snap.roster) ? snap.roster : null,
        });
      } catch (err) {
        console.error("bad snapshot frame", err);
      }
    });

    es.onmessage = (e: MessageEvent) => {
      if (gen !== sseConnectGen) return;
      try {
        const ev = JSON.parse(e.data);
        const cur = get().state ?? initialSpectateState();
        set({ state: reduceEvent(cur, ev) });
        if (ev.event_type === "belief_snapshot") {
          set({ insightBeliefs: mapBeliefEvent(ev.data) });
        } else if (ev.event_type === "vote_intention_snapshot") {
          set({ insightVote: mapVoteEvent(ev.data) });
        }
      } catch (err) {
        console.error("bad sse event", err);
      }
    };

    es.addEventListener("end", () => {
      if (gen === sseConnectGen) get().disconnectSpectate();
    });
    es.onerror = () => {
      if (gen !== sseConnectGen) return;
      set({ spectateError: "观战连接中断，请检查对局是否仍在进行或稍后重试。" });
    };
    set({ spectateSource: es });
  },

  disconnectSpectate: () => {
    sseConnectGen += 1;
    const es = get().spectateSource;
    if (es) es.close();
    set({ spectateSource: null });
  },

  pendingInput: null,
  playerToken: null,
  humanSeat: null,
  seatRunId: null,
  humanInputError: null,

  ingestSeatEvent: (ev) => {
    if (!ev || typeof ev !== "object") return false;
    const event = ev as AwaitingInputEvent;
    const t = event.event_type;
    if (t === "awaiting_input") {
      set({ pendingInput: event, humanInputError: null });
      return true;
    }
    if (t === "input_received" || t === "input_timeout") {
      const cur = get().pendingInput;
      if (cur && (event.request_id == null || event.request_id === cur.request_id)) {
        set({ pendingInput: null });
      }
      return true;
    }
    return false;
  },

  clearPendingInput: () => set({ pendingInput: null }),
  clearHumanInputError: () => set({ humanInputError: null }),

  submitHumanInput: async (selection) => {
    const { pendingInput, playerToken, seatRunId } = get();
    if (!pendingInput || !playerToken || !seatRunId) return;
    const [{ buildHumanPayload }, { ApiClient }] = await Promise.all([
      import("./lib/humanInput"),
      import("./api/client"),
    ]);
    const payload = buildHumanPayload(selection);
    try {
      await ApiClient.sendInput(seatRunId, {
        token: playerToken,
        request_id: pendingInput.request_id,
        kind: pendingInput.kind,
        payload,
      });
      set({ pendingInput: null, humanInputError: null });
    } catch (err) {
      console.error("Failed to submit human input:", err);
      set({
        humanInputError:
          err instanceof Error ? err.message : "提交操作失败，请重试。",
      });
    }
  },

  connectSeat: (runId, { seat, token }) => {
    get().disconnectSpectate();
    const gen = ++sseConnectGen;
    set({
      insightBeliefs: null,
      insightVote: null,
      spectateRoster: null,
      pendingInput: null,
      humanInputError: null,
      seatRunId: runId,
      playerToken: token,
      humanSeat: seat,
    });
    set({ state: initialSpectateState(), isLoading: false });

    const es = new EventSource(streamUrl(runId, "seat", seat, token));

    es.addEventListener("snapshot", (e: MessageEvent) => {
      if (gen !== sseConnectGen) return;
      try {
        const snap = JSON.parse(e.data);
        const cur = get().state ?? initialSpectateState();
        set({
          state: reduceEvent(cur, {
            ...snap,
            event_type: "snapshot",
            selfSeat: seat,
          }),
        });
      } catch (err) {
        console.error("bad snapshot frame", err);
      }
    });

    es.onmessage = (e: MessageEvent) => {
      if (gen !== sseConnectGen) return;
      try {
        const ev = JSON.parse(e.data);
        if (get().ingestSeatEvent(ev)) return;
        const cur = get().state ?? initialSpectateState();
        set({ state: reduceEvent(cur, { ...ev, selfSeat: seat }) });
      } catch (err) {
        console.error("bad sse event", err);
      }
    };

    es.addEventListener("end", () => {
      if (gen === sseConnectGen) get().disconnectSpectate();
    });
    es.onerror = () => {
      /* EventSource auto-reconnects */
    };
    set({ spectateSource: es });
  },
}));
