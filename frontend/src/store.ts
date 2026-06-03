import { create } from "zustand";
import { ViewResponse, ViewSnapshot, ViewEvent, RenderLog, SeatConfig } from "./types";
import { getApiKey, providerById } from "./lib/api-keys";

const API = "/api/v1";
const POLL_MS = 1000;

type Speed = 1 | 2 | 999; // 999 = 瞬间
type RevealView = "god" | "suspense";

interface GameStore {
  runId: string | null;
  status: ViewResponse["status"] | "idle";
  snapshot: ViewSnapshot | null;
  logs: RenderLog[];
  cursor: number;
  queue: ViewEvent[];
  isPlaying: boolean;
  speed: Speed;
  revealView: RevealView;
  error: string | null;

  startGame: (seats: SeatConfig[], opts?: { language?: string; enableSheriff?: boolean }) => Promise<void>;
  cancelGame: () => Promise<void>;
  togglePlay: () => void;
  setSpeed: (s: Speed) => void;
  setRevealView: (v: RevealView) => void;
  exitToSetup: () => void;
  _poll: () => Promise<void>;
  _drain: () => void;
}

let pollTimer: ReturnType<typeof setInterval> | null = null;
let drainTimer: ReturnType<typeof setInterval> | null = null;

function unwrap<T>(json: any): T {
  return (json && typeof json === "object" && "data" in json ? json.data : json) as T;
}

// 是否对该事件做悬念遮挡（仅前端）
function shouldMask(ev: ViewEvent, view: RevealView): boolean {
  if (view === "god") return false;
  return ev.reveal !== "now"; // suspense: on_death / on_game_end 暂时遮挡
}

function toRenderLog(ev: ViewEvent, view: RevealView): RenderLog {
  const masked = shouldMask(ev, view);
  let text = ev.text;
  if (ev.type === "speech") {
    text = masked ? "🌙 有角色在暗中交流…" : (ev.public_text || ev.text);
  } else if (masked) {
    text = ev.type === "skill" ? "🌙 夜间有角色行动了…" : ev.text;
  }
  return {
    seq: ev.seq,
    kind: ev.type,
    day: ev.day,
    speakerSeat: ev.speaker?.seat ?? null,
    speakerName: ev.speaker?.name ?? "",
    text,
    privateThought: view === "god" ? ev.private_thought ?? null : null,
    visibility: ev.visibility,
  };
}

export const useGameStore = create<GameStore>((set, get) => ({
  runId: null,
  status: "idle",
  snapshot: null,
  logs: [],
  cursor: 0,
  queue: [],
  isPlaying: true,
  speed: 1,
  revealView: "god",
  error: null,

  startGame: async (seats, opts) => {
    set({ status: "running", logs: [], cursor: 0, queue: [], snapshot: null, error: null, isPlaying: true });
    const players = seats.map((s) => ({
      name: s.name,
      model: s.model,
      base_url: s.base_url || providerById(s.provider)?.base_url,
      api_key: getApiKey(s.provider),
      temperature: s.temperature,
    }));
    try {
      const res = await fetch(`${API}/games/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          participation: "all_agent",
          rules: opts?.enableSheriff ? "badge_flow" : "basic",
          player_count: seats.length,
          badge_flow: !!opts?.enableSheriff,
          players,
        }),
      });
      if (!res.ok) {
        const msg = `start failed: HTTP ${res.status}`;
        set({ status: "error", error: msg });
        return;
      }
      const data = unwrap<{ run_id: string }>(await res.json());
      if (!data?.run_id) {
        set({ status: "error", error: "start failed: no run_id" });
        return;
      }
      set({ runId: data.run_id });
      if (pollTimer) clearInterval(pollTimer);
      if (drainTimer) clearInterval(drainTimer);
      pollTimer = setInterval(() => get()._poll(), POLL_MS);
      drainTimer = setInterval(() => get()._drain(), 220);
      get()._poll();
    } catch (err) {
      console.error("startGame failed", err);
      set({ status: "error", error: String(err) });
    }
  },

  _poll: async () => {
    const { runId, cursor } = get();
    if (!runId) return;
    try {
      const res = await fetch(`${API}/games/${runId}/view?since=${cursor}`);
      if (!res.ok) {
        set({ status: "error", error: `view failed: HTTP ${res.status}` });
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        return;
      }
      const view = unwrap<ViewResponse>(await res.json());
      set((st) => ({
        snapshot: view.snapshot,
        cursor: view.cursor,
        status: view.status,
        error: view.error,
        queue: [...st.queue, ...view.events],
      }));
      if (view.status === "ended" || view.status === "cancelled" || view.status === "error") {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      }
    } catch (err) {
      console.error("poll failed", err);
    }
  },

  _drain: () => {
    const { isPlaying, queue, speed, revealView } = get();
    if (!isPlaying || queue.length === 0) return;
    const take = speed === 999 ? queue.length : speed;
    const batch = queue.slice(0, take);
    const rest = queue.slice(take);
    set((st) => ({
      queue: rest,
      logs: [...st.logs, ...batch.map((ev) => toRenderLog(ev, revealView))],
    }));
  },

  cancelGame: async () => {
    const { runId } = get();
    if (runId) {
      try { await fetch(`${API}/games/${runId}/cancel`, { method: "POST" }); } catch { /* ignore */ }
    }
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (drainTimer) { clearInterval(drainTimer); drainTimer = null; }
    set({ status: "cancelled", isPlaying: false });
  },

  togglePlay: () => set((st) => ({ isPlaying: !st.isPlaying })),
  setSpeed: (s) => set({ speed: s }),
  setRevealView: (v) => set({ revealView: v }),

  exitToSetup: () => {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (drainTimer) { clearInterval(drainTimer); drainTimer = null; }
    set({ runId: null, status: "idle", snapshot: null, logs: [], cursor: 0, queue: [], error: null });
  },
}));
