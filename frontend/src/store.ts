import { create } from "zustand";
import {
  ControlRequest, GamePhase, GameStateResponse, PlayState, RenderLog,
  SeatConfig, StreamEvent, Visibility,
} from "./types";
import { API, fetchState, postControl, streamUrl } from "./lib/api";
import { getApiKey, providerById } from "./lib/api-keys";

type Speed = 1 | 2 | 4;
type RevealView = "god" | "suspense";

interface GameStore {
  runId: string | null;
  status: GameStateResponse["status"] | "idle";
  gameState: GameStateResponse | null;
  logs: RenderLog[];
  cursor: number;
  queue: StreamEvent[];
  playState: PlayState | "playing" | "paused";
  speed: Speed;
  revealView: RevealView;
  error: string | null;

  startGame: (seats: SeatConfig[], opts?: { language?: string; enableSheriff?: boolean }) => Promise<void>;
  cancelGame: () => Promise<void>;
  controlGame: (action: "pause" | "resume" | "step") => Promise<void>;
  stepGame: () => Promise<void>;
  setSpeed: (s: Speed) => Promise<void>;
  setRevealView: (v: RevealView) => void;
  isGameOver: () => boolean;
  exitToSetup: () => void;
  _openStream: (runId: string) => void;
  _refreshState: () => Promise<void>;
  _drain: () => void;
}

let eventSource: EventSource | null = null;
let stateTimer: ReturnType<typeof setInterval> | null = null;
let drainTimer: ReturnType<typeof setInterval> | null = null;

const STATE_REFRESH_MS = 1500; // authoritative phase/round/play_state poll (cheap, no events)
const DRAIN_MS = 220;

function teardown() {
  if (eventSource) { eventSource.close(); eventSource = null; }
  if (stateTimer) { clearInterval(stateTimer); stateTimer = null; }
  if (drainTimer) { clearInterval(drainTimer); drainTimer = null; }
}

function shouldMask(ev: StreamEvent, view: RevealView): boolean {
  if (view === "god") return false;
  return ev.reveal !== "now"; // suspense: on_death / on_game_end 暂时遮挡
}

function eventText(ev: StreamEvent): string {
  if (ev.type === "speech") return ev.public_text || ev.text || "";
  if (ev.type === "skill" && ev.skill) {
    const a = ev.skill.actor?.seat ?? "?";
    const t = ev.skill.target?.seat;
    return t != null ? `技能：${ev.skill.kind}（${a}号 → ${t}号）` : `技能：${ev.skill.kind}（${a}号）`;
  }
  if (ev.type === "vote" && ev.vote) {
    return `投票：${ev.vote.voter?.seat ?? "?"}号 → ${ev.vote.target?.seat ?? "?"}号`;
  }
  if (ev.type === "death" && ev.death) {
    return `出局：${ev.death.seat ?? "?"}号（${ev.death.cause ?? "未知"}）`;
  }
  return ev.text || ev.name || "";
}

function toRenderLog(ev: StreamEvent, view: RevealView): RenderLog {
  const masked = shouldMask(ev, view);
  let text = eventText(ev);
  if (masked) {
    text = ev.type === "speech" ? "🌙 有角色在暗中交流…" : "🌙 夜间有角色行动了…";
  }
  return {
    seq: ev.seq,
    kind: ev.type,
    round: ev.round,
    speakerSeat: ev.speaker?.seat ?? ev.skill?.actor?.seat ?? null,
    speakerName: ev.speaker?.name ?? "",
    text,
    privateThought: view === "god" ? ev.private_thought ?? null : null,
    visibility: ev.visibility as Visibility,
  };
}

export const useGameStore = create<GameStore>((set, get) => ({
  runId: null,
  status: "idle",
  gameState: null,
  logs: [],
  cursor: 0,
  queue: [],
  playState: "playing",
  speed: 1,
  revealView: "god",
  error: null,

  startGame: async (seats, opts) => {
    teardown();
    set({ status: "running", logs: [], cursor: 0, queue: [], gameState: null, error: null, playState: "playing" });
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
      if (!res.ok) { set({ status: "error", error: `start failed: HTTP ${res.status}` }); return; }
      const body = await res.json();
      const data = (body && "data" in body ? body.data : body) as { run_id?: string };
      if (!data?.run_id) { set({ status: "error", error: "start failed: no run_id" }); return; }
      set({ runId: data.run_id });
      get()._openStream(data.run_id);
      stateTimer = setInterval(() => get()._refreshState(), STATE_REFRESH_MS);
      drainTimer = setInterval(() => get()._drain(), DRAIN_MS);
      get()._refreshState();
    } catch (err) {
      console.error("startGame failed", err);
      set({ status: "error", error: String(err) });
    }
  },

  // SSE subscription — relies on the browser's built-in auto-reconnect + Last-Event-ID.
  _openStream: (runId) => {
    if (eventSource) eventSource.close();
    const es = new EventSource(streamUrl(runId));
    es.onmessage = (msg: MessageEvent) => {
      try {
        const ev = JSON.parse(msg.data) as StreamEvent;
        set((st) => ({
          queue: [...st.queue, ev],
          cursor: Math.max(st.cursor, ev.seq),
        }));
        // Drain immediately while playing so the render buffer keeps up; when
        // paused the periodic drainTimer takes over once resumed.
        if (get().playState === "playing") get()._drain();
      } catch (err) {
        console.error("bad SSE payload", err);
      }
    };
    es.onerror = () => { /* browser auto-reconnects with Last-Event-ID; nothing to do */ };
    eventSource = es;
  },

  // Authoritative phase/round/play_state/winner + full-snapshot fallback.
  _refreshState: async () => {
    const { runId } = get();
    if (!runId) return;
    try {
      const state = await fetchState(runId);
      set({ gameState: state, status: state.status, playState: state.play_state, speed: state.speed, error: state.error });
      if (state.phase === GamePhase.ended || state.status === "cancelled" || state.status === "error") {
        if (stateTimer) { clearInterval(stateTimer); stateTimer = null; }
        if (eventSource) { eventSource.close(); eventSource = null; }
      }
    } catch (err) {
      console.error("state refresh failed", err);
    }
  },

  _drain: () => {
    const { playState, queue, speed, revealView } = get();
    if (playState !== "playing" || queue.length === 0) return;
    const take = Math.max(speed, 1);
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
    teardown();
    set({ status: "cancelled" });
  },

  controlGame: async (action) => {
    const { runId } = get();
    if (!runId) return;
    try {
      const resp = await postControl(runId, { action } as ControlRequest);
      set({ playState: resp.play_state, speed: resp.speed as Speed });
    } catch (err) {
      console.error("control failed", err);
    }
  },

  stepGame: async () => {
    const { runId } = get();
    if (!runId) return;
    try {
      const resp = await postControl(runId, { action: "step" });
      set({ playState: resp.play_state });
    } catch (err) {
      console.error("step failed", err);
    }
  },

  setSpeed: async (s) => {
    const { runId } = get();
    set({ speed: s });
    if (!runId) return;
    try {
      const resp = await postControl(runId, { action: "speed", value: s });
      set({ speed: resp.speed as Speed, playState: resp.play_state });
    } catch (err) {
      console.error("speed failed", err);
    }
  },

  setRevealView: (v) => set({ revealView: v }),

  isGameOver: () => get().gameState?.phase === GamePhase.ended,

  exitToSetup: () => {
    teardown();
    set({ runId: null, status: "idle", gameState: null, logs: [], cursor: 0, queue: [], error: null, playState: "playing" });
  },
}));
