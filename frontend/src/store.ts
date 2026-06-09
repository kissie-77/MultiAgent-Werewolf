import { create } from "zustand";
import { GameState } from "./types";
import type { ActiveCast } from "./types";
import type { AwaitingInputEvent } from "./api/types";
import type { HumanInputSelection } from "./lib/humanInput";
import {
  initialSpectateState,
  reduceEvent,
} from "./lib/gameReducer";
import { streamUrl } from "./api/sse";
import { mapBeliefEvent, mapVoteEvent, mapSpeakerSeat, mapWolfCampEvent } from "./lib/insightMap";
import { castFromSkillSubmit, castFromEvent, effectTypeForRole } from "./lib/castMap";
import { soundManager } from "./audio/soundManager";
import { effectTypeSfx, eventSfx, type SfxId } from "./audio/soundMap";
import type { SseEvent } from "./lib/gameReducer";
import type { CoarseStage } from "./lib/phaseStage";
import type { WolfCampMindV2 } from "./lib/godRoleIntel";

function readAudioPref(): { muted: boolean; volume: number } {
  try {
    const raw = localStorage.getItem("ww_audio");
    if (raw) {
      const p = JSON.parse(raw);
      return { muted: !!p.muted, volume: typeof p.volume === "number" ? p.volume : 0.8 };
    }
  } catch { /* ignore */ }
  return { muted: false, volume: 0.8 };
}
function writeAudioPref(p: { muted: boolean; volume: number }): void {
  try { localStorage.setItem("ww_audio", JSON.stringify(p)); } catch { /* ignore */ }
}

/**
 * 单点派发"技能/事件"音。
 * 技能音走 `role_acting`：引擎对每个夜间行动者都稳定下发（细分结果事件 seer_checked/
 * witch_* 多数局根本不发），且只有 god 流携带真实 role。故仅 god 视角播技能音；座位视角
 * 播他人 role_acting 会泄漏身份，本人技能改由 submitHumanInput 播。事件音（死亡/放逐/计票/
 * 胜负等公共事件）两视角都播，不泄漏。
 */
function dispatchSseSound(ev: SseEvent, view: "god" | "seat"): void {
  if (view === "god" && ev.event_type === "role_acting") {
    const role = String(ev.data?.role ?? "");
    if (role) {
      soundManager.playGameplay(effectTypeSfx[effectTypeForRole(role)], ev.event_id);
      return;
    }
  }
  const sid: SfxId | null = eventSfx(ev);
  if (sid) soundManager.playGameplay(sid, ev.event_id);
}

/** Monotonic token so stale SSE connect callbacks are ignored after disconnect/switch. */
let sseConnectGen = 0;

interface GameStore {
  state: GameState | null;
  isLoading: boolean;
  setupCount: number | null;
  insightEnabled: boolean;
  audioMuted: boolean;
  sfxVolume: number;
  setAudioMuted: (m: boolean) => void;
  setSfxVolume: (v: number) => void;
  setSetupCount: (count: number | null) => void;
  setInsightEnabled: (enabled: boolean) => void;
  exitGame: () => void;

  // Live spectate (SSE god view)
  spectateSource: EventSource | null;
  spectateError: string | null;
  insightBeliefs: import("./api/insightTypes").BeliefSnapshot[] | null;
  insightVote: import("./api/insightTypes").VoteIntentionSnapshot | null;
  insightSpeakerSeat: number | null;
  insightWolfCampMinds: Record<number, WolfCampMindV2> | null;
  spectateRoster: import("./lib/insightMap").RosterEntry[] | null;
  /** Transient phase-transition signal (drives the cinematic card, flash, and camera). */
  stageFx: { stage: CoarseStage; nonce: number } | null;
  fireStageFx: (stage: CoarseStage) => void;
  clearStageFx: () => void;
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

  // Skill-cast cinematic + target selection (shared by sidebar/dock/3D board)
  activeCast: ActiveCast | null;
  triggerCast: (cast: ActiveCast) => void;
  clearCast: () => void;
  clearSkillFx: () => void;

  /** Visual target selection (seat view): mirrored to the dock + 3D board ring. */
  selectedTargetSeat: number | null;
  setSelectedTargetSeat: (seat: number | null) => void;
}

export const useGameStore = create<GameStore>((set, get) => ({
  state: null,
  isLoading: false,
  setupCount: null,
  insightEnabled: true,
  audioMuted: readAudioPref().muted,
  sfxVolume: readAudioPref().volume,
  setAudioMuted: (m) => {
    soundManager.setMuted(m);
    writeAudioPref({ muted: m, volume: get().sfxVolume });
    set({ audioMuted: m });
  },
  setSfxVolume: (v) => {
    soundManager.setSfxVolume(v);
    writeAudioPref({ muted: get().audioMuted, volume: v });
    set({ sfxVolume: v });
  },

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
  insightSpeakerSeat: null,
  insightWolfCampMinds: null,
  spectateRoster: null,
  stageFx: null,

  fireStageFx: (stage) =>
    set((s) => ({ stageFx: { stage, nonce: (s.stageFx?.nonce ?? 0) + 1 } })),
  clearStageFx: () => set({ stageFx: null }),

  connectSpectate: (runId) => {
    get().disconnectSpectate();
    const gen = ++sseConnectGen;
    set({
      insightBeliefs: null,
      insightVote: null,
      insightSpeakerSeat: null,
      insightWolfCampMinds: null,
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
        const cast = castFromEvent(ev, get().state?.players);
        if (cast) get().triggerCast(cast);
        dispatchSseSound(ev, "god");
        if (ev.event_type === "belief_snapshot") {
          set({ insightBeliefs: mapBeliefEvent(ev.data), insightSpeakerSeat: mapSpeakerSeat(ev.data) });
        } else if (ev.event_type === "vote_intention_snapshot") {
          set({ insightVote: mapVoteEvent(ev.data) });
        } else if (ev.event_type === "wolf_camp_snapshot") {
          set({ insightWolfCampMinds: mapWolfCampEvent(ev.data) });
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
    set({ spectateSource: null, stageFx: null });
  },

  pendingInput: null,
  playerToken: null,
  humanSeat: null,
  seatRunId: null,
  humanInputError: null,

  activeCast: null,
  selectedTargetSeat: null,
  triggerCast: (cast) => set({ activeCast: cast }),
  clearCast: () => set({ activeCast: null }),
  setSelectedTargetSeat: (seat) => set({ selectedTargetSeat: seat }),

  ingestSeatEvent: (ev) => {
    if (!ev || typeof ev !== "object") return false;
    const event = ev as AwaitingInputEvent;
    const t = event.event_type;
    if (t === "awaiting_input") {
      set({ pendingInput: event, humanInputError: null, selectedTargetSeat: null });
      soundManager.playUi("ui_your_turn");
      return true;
    }
    if (t === "input_received" || t === "input_timeout") {
      const cur = get().pendingInput;
      if (cur && (event.request_id == null || event.request_id === cur.request_id)) {
        set({ pendingInput: null });
      }
      if (t === "input_timeout") soundManager.playUi("ui_timeout");
      return true;
    }
    return false;
  },

  clearPendingInput: () => set({ pendingInput: null }),
  clearHumanInputError: () => set({ humanInputError: null }),

  clearSkillFx: () => {
    const cur = get().state;
    if (cur) set({ state: { ...cur, skillFx: null } });
  },

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
      soundManager.playUi("ui_submit");
      // Fire the local tarot-cast cinematic for the human's own skill action.
      const kind = pendingInput.kind;
      const players = get().state?.players ?? [];
      const selfRole = pendingInput.self_role ?? players.find((p) => p.isUser)?.role ?? "";
      if (selfRole && (kind === "seat" || kind === "witch")) {
        const targetSeat = get().selectedTargetSeat;
        const targetName =
          targetSeat != null ? players.find((p) => p.id === targetSeat)?.name ?? null : null;
        get().triggerCast(
          castFromSkillSubmit({
            selfRole,
            selfName: players.find((p) => p.isUser)?.name ?? "你",
            targetSeat,
            targetName,
          })
        );
      }
      // The human's own skill sound plays here: seat view does not sound others'
      // role_acting (would leak), and the engine rarely emits the specific result
      // event, so submit-time is the reliable moment. Generic by role.
      if (selfRole && (kind === "seat" || kind === "witch")) {
        soundManager.playGameplay(effectTypeSfx[effectTypeForRole(selfRole)]);
      }
      set({ selectedTargetSeat: null });
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
      insightSpeakerSeat: null,
      insightWolfCampMinds: null,
      spectateRoster: null,
      pendingInput: null,
      humanInputError: null,
      selectedTargetSeat: null,
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
        // Seat view: the human's own skill is announced by castFromSkillSubmit; only
        // surface public 身份揭示 reveals here to avoid double-firing the same action.
        if (ev.event_type === "role_revealed") {
          const cast = castFromEvent(ev, get().state?.players);
          if (cast) get().triggerCast(cast);
        }
        dispatchSseSound(ev, "seat");
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

{
  const init = useGameStore.getState();
  soundManager.setMuted(init.audioMuted);
  soundManager.setSfxVolume(init.sfxVolume);
}
