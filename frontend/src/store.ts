import { create } from "zustand";
import { GameState, Player } from "./types";
import { getCustomApiKey } from "./lib/config";
import type { AwaitingInputEvent } from "./api/types";
import type { HumanInputSelection } from "./lib/humanInput";

interface GameStore {
  state: GameState | null;
  selectedCardId: number | null;
  isLoading: boolean;
  userSpeechText: string;
  isAutoPlaying: boolean;
  setupCount: number | null;
  
  // Skill casting overlay states
  activeCast: {
    casterId: number | "USER";
    casterName: string;
    role: string;
    skillName: string;
    skillSub: string;
    targetId: number | null;
    targetName: string | null;
    effectType: "inspect" | "heal" | "poison" | "bite" | "shoot" | "vote" | "rally";
  } | null;
  triggerCast: (castDetails: any) => void;
  clearCast: () => void;
  
  // Custom skill target picking dialog state
  targetingSkill: {
    type: "NIGHT_KILL" | "NIGHT_INSPECT" | "NIGHT_POISON" | "NIGHT_HEAL" | "USER_VOTE" | "HUNTER_SHOOT";
    title: string;
    subtitle: string;
    description: string;
  } | null;
  setTargetingSkill: (skill: {
    type: "NIGHT_KILL" | "NIGHT_INSPECT" | "NIGHT_POISON" | "NIGHT_HEAL" | "USER_VOTE" | "HUNTER_SHOOT";
    title: string;
    subtitle: string;
    description: string;
  } | null) => void;
  
  // Actions
  fetchState: () => Promise<void>;
  resetGame: (userRole?: string, playerCount?: number, gameMode?: "llmOnly" | "humanVsAI", startImmediately?: boolean, hasSheriff?: boolean) => Promise<void>;
  submitUserSpeech: () => Promise<void>;
  castVote: () => Promise<void>;
  castSheriffVote: (overrideTargetId?: number | null) => Promise<void>;
  simulateNextAI: () => Promise<void>;
  nightSkillAction: (actionType: "NIGHT_KILL" | "NIGHT_INSPECT" | "NIGHT_SAVED_OR_POISON" | "HUNTER_SHOOT", targetId: number, additional?: any) => Promise<void>;
  transitionToDebate: () => Promise<void>;
  sheriffRunResolve: (userRuns: boolean) => Promise<void>;
  exitGame: () => Promise<void>;
  setSelectedCardId: (id: number | null) => void;
  setUserSpeechText: (text: string) => void;
  toggleAutoPlay: () => void;
  setSetupCount: (count: number | null) => void;

  // Live spectate (SSE god-view)
  spectateSource: EventSource | null;
  insightBeliefs: import("./api/insightTypes").BeliefSnapshot[] | null;
  insightVote: import("./api/insightTypes").VoteIntentionSnapshot | null;
  spectateRoster: import("./lib/insightMap").RosterEntry[] | null;
  connectSpectate: (runId: string) => void;
  disconnectSpectate: () => void;

  // Human-vs-AI seat view (SSE seat stream + awaiting_input bridge)
  pendingInput: AwaitingInputEvent | null;
  playerToken: string | null;
  humanSeat: number | null;
  seatRunId: string | null;
  connectSeat: (runId: string, opts: { seat: number; token: string }) => void;
  ingestSeatEvent: (ev: any) => boolean;
  submitHumanInput: (selection: HumanInputSelection) => Promise<void>;
  clearPendingInput: () => void;
}

export const useGameStore = create<GameStore>((set, get) => ({
  state: null,
  selectedCardId: null,
  isLoading: false,
  userSpeechText: "",
  isAutoPlaying: false,
  setupCount: null,
  
  activeCast: null,
  triggerCast: (castDetails) => set({ activeCast: castDetails }),
  clearCast: () => set({ activeCast: null }),
  
  targetingSkill: null,
  setTargetingSkill: (skill) => set({ targetingSkill: skill }),
  
  setSetupCount: (count) => set({ setupCount: count }),

  fetchState: async () => {
    try {
      const res = await fetch("/api/game/state", {
        headers: { "X-Deepseek-Api-Key": getCustomApiKey() }
      });
      const data = await res.json();
      set({ state: data });
    } catch (err) {
      console.error("Failed to fetch game state:", err);
    }
  },

  resetGame: async (userRole = "预言家", playerCount = 6, gameMode = "humanVsAI", startImmediately = false, hasSheriff = false) => {
    if (get().isLoading) return;
    set({ isLoading: true, selectedCardId: null, userSpeechText: "" });
    try {
      const res = await fetch("/api/game/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ userRole, playerCount, gameMode, startImmediately, hasSheriff })
      });
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed to reset game:", err);
      set({ isLoading: false });
    }
  },

  submitUserSpeech: async () => {
    if (get().isLoading) return;
    const { userSpeechText } = get();
    set({ isLoading: true });
    try {
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ action: "SPEECH_SUBMIT", text: userSpeechText })
      });
      const data = await res.json();
      set({ state: data, userSpeechText: "", selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to submit speech:", err);
      set({ isLoading: false });
    }
  },

  castVote: async () => {
    const { selectedCardId, isLoading } = get();
    if (isLoading) return;
    if (selectedCardId === null) return;
    
    // Skill Cast Trigger before Vote Action goes live!
    const state = get().state;
    if (state) {
      const userPlayer = state.players.find(p => p.isUser);
      const targetPlayer = state.players.find(p => p.id === selectedCardId);
      if (userPlayer) {
        let skillName = "流放投票";
        let skillSub = "EXILE VOTE";
        let effectType: "inspect" | "heal" | "poison" | "bite" | "shoot" | "vote" | "rally" = "vote";

        if (userPlayer.role === "村民") {
          skillName = "流放投票";
          skillSub = "VILLAGER VOTE";
          effectType = "vote";
        } else if (userPlayer.role === "预言家") {
          skillName = "流放投票";
          skillSub = "SEER VOTE";
          effectType = "inspect";
        } else if (userPlayer.role === "狼人") {
          skillName = "流放投票";
          skillSub = "WEREWOLF VOTE";
          effectType = "bite";
        } else if (userPlayer.role === "女巫") {
          skillName = "流放投票";
          skillSub = "WITCH VOTE";
          effectType = "poison";
        } else if (userPlayer.role === "猎人") {
          skillName = "流放投票";
          skillSub = "HUNTER VOTE";
          effectType = "shoot";
        }

        get().triggerCast({
          casterId: userPlayer.id,
          casterName: `你 (玩家 ${userPlayer.id} 号)`,
          role: userPlayer.role,
          skillName,
          skillSub,
          targetId: selectedCardId,
          targetName: targetPlayer ? targetPlayer.name : `玩家 ${selectedCardId} 号`,
          effectType
        });
      }
    }

    set({ isLoading: true });
    try {
      // Small visual delay to appreciate the overlay animation!
      await new Promise(resolve => setTimeout(resolve, 2400));
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ action: "USER_VOTE", targetId: selectedCardId })
      });
      const data = await res.json();
      set({ state: data, selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to cast vote:", err);
      set({ isLoading: false });
    }
  },

  castSheriffVote: async (overrideTargetId?: number | null) => {
    const { selectedCardId, state, isLoading } = get();
    if (isLoading) return;
    if (!state) return;
    
    // Allow override for skipping
    const finalTargetId = overrideTargetId !== undefined ? overrideTargetId : selectedCardId;

    const userPlayer = state.players.find(p => p.isUser);
    const targetPlayer = finalTargetId ? state.players.find(p => p.id === finalTargetId) : null;

    if (userPlayer && finalTargetId !== null) {
      get().triggerCast({
        casterId: userPlayer.id,
        casterName: `你 (玩家 ${userPlayer.id} 号)`,
        role: userPlayer.role,
        skillName: "选票警长",
        skillSub: "SHERIFF VOTE",
        targetId: finalTargetId,
        targetName: targetPlayer ? targetPlayer.name : `玩家 ${finalTargetId} 号`,
        effectType: "rally"
      });
    }

    set({ isLoading: true });
    try {
      if (finalTargetId !== null) {
        await new Promise(resolve => setTimeout(resolve, 2400));
      }
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ action: "SHERIFF_VOTE", targetId: finalTargetId })
      });
      const data = await res.json();
      set({ state: data, selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to cast sheriff vote:", err);
      set({ isLoading: false });
    }
  },

  simulateNextAI: async () => {
    if (get().isLoading) return;
    set({ isLoading: true });
    try {
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ action: "SIMULATE_NEXT_SPEAKER" })
      });
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed to simulate speaker:", err);
      set({ isLoading: false });
    }
  },

  nightSkillAction: async (actionType, targetId, additional) => {
    if (get().isLoading) return;
    // Skill Cast trigger before Night Skill Action goes live!
    const state = get().state;
    if (state) {
      const userPlayer = state.players.find(p => p.isUser);
      const targetPlayer = state.players.find(p => p.id === targetId);
      if (userPlayer) {
        let skillName = "夜间行动";
        let skillSub = "NIGHT ACTION";
        let effectType: "inspect" | "heal" | "poison" | "bite" | "shoot" | "vote" | "rally" = "inspect";

        if (actionType === "NIGHT_INSPECT") {
          skillName = "预言查验";
          skillSub = "SEER INSPECT";
          effectType = "inspect";
        } else if (actionType === "NIGHT_SAVED_OR_POISON") {
          if (additional?.saved) {
            skillName = "女巫解药";
            skillSub = "WITCH ANTIDOTE";
            effectType = "heal";
          } else {
            skillName = "女巫毒药";
            skillSub = "WITCH POISON";
            effectType = "poison";
          }
          } else if (actionType === "NIGHT_KILL") {
          skillName = "狼人袭击";
          skillSub = "WEREWOLF ATTACK";
          effectType = "bite";
        } else if (actionType === "HUNTER_SHOOT") {
          skillName = "猎人开枪";
          skillSub = "HUNTER SHOOT";
          effectType = "shoot";
        }

        get().triggerCast({
          casterId: userPlayer.id,
          casterName: `你 (玩家 ${userPlayer.id} 号)`,
          role: userPlayer.role,
          skillName,
          skillSub,
          targetId: targetId || null,
          targetName: targetPlayer ? targetPlayer.name : (targetId ? `玩家 ${targetId} 号` : null),
          effectType
        });
      }
    }

    set({ isLoading: true });
    try {
      // Delay slightly for the cinematic effect to render smoothly
      await new Promise(resolve => setTimeout(resolve, 2400));
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ action: actionType, targetId, ...additional })
      });
      const data = await res.json();
      set({ state: data, selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to exert night action:", err);
      set({ isLoading: false });
    }
  },

  transitionToDebate: async () => {
    if (get().isLoading) return;
    set({ isLoading: true });
    try {
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ action: "TRANSITION_TO_DEBATE" })
      });
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed executing transition:", err);
      set({ isLoading: false });
    }
  },

  sheriffRunResolve: async (userRuns: boolean) => {
    if (get().isLoading) return;
    set({ isLoading: true });
    try {
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Deepseek-Api-Key": getCustomApiKey() },
        body: JSON.stringify({ action: "SHERIFF_RUN_RESOLVE", userRuns })
      });
      const data = await res.json();
      set({ state: data, isLoading: false, selectedCardId: null });
    } catch (err) {
      console.error("Sheriff run resolve failed:", err);
      set({ isLoading: false });
    }
  },

  exitGame: async () => {
    set({ isLoading: true, isAutoPlaying: false });
    try {
      const res = await fetch("/api/game/exit", {
        method: "POST",
        headers: { "X-Deepseek-Api-Key": getCustomApiKey() }
      });
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed executing exitGame:", err);
      set({ isLoading: false });
    }
  },

  setSelectedCardId: (id) => set({ selectedCardId: id }),
  setUserSpeechText: (text) => set({ userSpeechText: text }),
  toggleAutoPlay: () => set((state) => ({ isAutoPlaying: !state.isAutoPlaying })),

  spectateSource: null,
  insightBeliefs: null,
  insightVote: null,
  spectateRoster: null,
  connectSpectate: (runId) => {
    get().disconnectSpectate();
    set({ insightBeliefs: null, insightVote: null, spectateRoster: null });
    Promise.all([import("./lib/gameReducer"), import("./api/sse"), import("./lib/insightMap")]).then(
      ([{ initialSpectateState, reduceEvent }, { streamUrl }, { mapBeliefEvent, mapVoteEvent }]) => {
        set({ state: initialSpectateState(), isLoading: false });
        const es = new EventSource(streamUrl(runId, "god"));

        // Named "snapshot" frame: inject event_type so the reducer's snapshot
        // case fires (roster -> seats), and stash the god roster for insight.
        es.addEventListener("snapshot", (e: MessageEvent) => {
          try {
            const snap = JSON.parse(e.data);
            const cur = get().state ?? initialSpectateState();
            set({
              state: reduceEvent(cur, { ...snap, event_type: "snapshot" }),
              spectateRoster: Array.isArray(snap.roster) ? snap.roster : null,
            });
          } catch (err) { console.error("bad snapshot frame", err); }
        });

        // Unnamed game/insight events (event_type lives inside data JSON).
        es.onmessage = (e: MessageEvent) => {
          try {
            const ev = JSON.parse(e.data);
            const cur = get().state ?? initialSpectateState();
            set({ state: reduceEvent(cur, ev) });
            if (ev.event_type === "belief_snapshot") set({ insightBeliefs: mapBeliefEvent(ev.data) });
            else if (ev.event_type === "vote_intention_snapshot") set({ insightVote: mapVoteEvent(ev.data) });
          } catch (err) { console.error("bad sse event", err); }
        };

        es.addEventListener("end", () => { get().disconnectSpectate(); });
        es.onerror = () => { /* EventSource auto-reconnects */ };
        set({ spectateSource: es });
      },
    );
  },
  disconnectSpectate: () => {
    const es = get().spectateSource;
    if (es) es.close();
    set({ spectateSource: null });
  },

  // --- Human-vs-AI seat view ---------------------------------------------
  pendingInput: null,
  playerToken: null,
  humanSeat: null,
  seatRunId: null,

  // Capture the awaiting_input bridge events on the seat stream. Returns true
  // when the event was consumed (so the caller skips the normal reducer).
  ingestSeatEvent: (ev) => {
    const t = ev?.event_type;
    if (t === "awaiting_input") {
      set({ pendingInput: ev as AwaitingInputEvent });
      return true;
    }
    if (t === "input_received" || t === "input_timeout") {
      const cur = get().pendingInput;
      if (cur && (ev.request_id == null || ev.request_id === cur.request_id)) {
        set({ pendingInput: null });
      }
      return true;
    }
    return false;
  },

  clearPendingInput: () => set({ pendingInput: null }),

  submitHumanInput: async (selection) => {
    const { pendingInput, playerToken, seatRunId } = get();
    if (!pendingInput || !playerToken || !seatRunId) return;
    const [{ buildHumanPayload }, { ApiClient }] = await Promise.all([
      import("./lib/humanInput"),
      import("./api/client"),
    ]);
    const payload = buildHumanPayload(selection);
    try {
      const res = await ApiClient.sendInput(seatRunId, {
        token: playerToken,
        request_id: pendingInput.request_id,
        kind: pendingInput.kind,
        payload,
      });
      if (res.accepted) {
        set({ pendingInput: null });
      }
    } catch (err) {
      console.error("Failed to submit human input:", err);
    }
  },

  connectSeat: (runId, { seat, token }) => {
    get().disconnectSpectate();
    set({
      insightBeliefs: null,
      insightVote: null,
      spectateRoster: null,
      pendingInput: null,
      seatRunId: runId,
      playerToken: token,
      humanSeat: seat,
    });
    Promise.all([import("./lib/gameReducer"), import("./api/sse"), import("./lib/insightMap")]).then(
      ([{ initialSpectateState, reduceEvent }, { streamUrl }, { mapBeliefEvent, mapVoteEvent }]) => {
        set({ state: initialSpectateState(), isLoading: false });
        const es = new EventSource(streamUrl(runId, "seat", seat, token));

        es.addEventListener("snapshot", (e: MessageEvent) => {
          try {
            const snap = JSON.parse(e.data);
            const cur = get().state ?? initialSpectateState();
            set({ state: reduceEvent(cur, { ...snap, event_type: "snapshot" }) });
          } catch (err) { console.error("bad snapshot frame", err); }
        });

        es.onmessage = (e: MessageEvent) => {
          try {
            const ev = JSON.parse(e.data);
            // awaiting_input / input_* bridge events drive the human panel.
            if (get().ingestSeatEvent(ev)) return;
            const cur = get().state ?? initialSpectateState();
            set({ state: reduceEvent(cur, ev) });
            if (ev.event_type === "belief_snapshot") set({ insightBeliefs: mapBeliefEvent(ev.data) });
            else if (ev.event_type === "vote_intention_snapshot") set({ insightVote: mapVoteEvent(ev.data) });
          } catch (err) { console.error("bad sse event", err); }
        };

        es.addEventListener("end", () => { get().disconnectSpectate(); });
        es.onerror = () => { /* EventSource auto-reconnects */ };
        set({ spectateSource: es });
      },
    );
  },
}));
