import { create } from "zustand";
import { fetchWithRetry } from "./api/retry";
import { GameState, NightSkillAdditional } from "./types";

const EMPTY_START_STATE: GameState = {
  players: [],
  dayNumber: 0,
  phase: "START_SCREEN",
  currentSpeakerId: null,
  countdown: 0,
  speechLogs: [],
  narration: "",
  winner: null,
  wolfKilledTarget: null,
  witchSaved: false,
  witchPoisonedTarget: null,
  seerVerifiedTarget: null,
  seerVerificationResult: null,
  victimId: null,
  discussionIndex: 0,
  executionId: null,
};

const IN_GAME_PHASES = new Set<GameState["phase"]>([
  "ROLE_CHOICE",
  "NIGHT_WOLF",
  "NIGHT_SEER",
  "NIGHT_WITCH",
  "DAY_ANNOUNCEMENT",
  "DAY_DEBATE",
  "DAY_VOTE",
  "GAME_OVER",
]);

interface GameStore {
  state: GameState | null;
  selectedCardId: number | null;
  isLoading: boolean;
  userSpeechText: string;
  isAutoPlaying: boolean;
  setupCount: number | null;
  
  // Actions
  fetchState: () => Promise<void>;
  resetGame: (userRole?: "预言家" | "女巫" | "猎人" | "狼人" | "村民", playerCount?: number, gameMode?: "llmOnly" | "humanVsAI", startImmediately?: boolean) => Promise<void>;
  submitUserSpeech: () => Promise<void>;
  castVote: () => Promise<void>;
  simulateNextAI: () => Promise<void>;
  nightSkillAction: (actionType: "NIGHT_KILL" | "NIGHT_INSPECT" | "NIGHT_SAVED_OR_POISON", targetId: number, additional?: NightSkillAdditional) => Promise<void>;
  transitionToDebate: () => Promise<void>;
  exitGame: () => Promise<void>;
  setSelectedCardId: (id: number | null) => void;
  setUserSpeechText: (text: string) => void;
  toggleAutoPlay: () => void;
  setSetupCount: (count: number | null) => void;
}

async function postJson(path: string, body?: unknown): Promise<Response> {
  return fetchWithRetry(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export const useGameStore = create<GameStore>((set, get) => ({
  state: null,
  selectedCardId: null,
  isLoading: false,
  userSpeechText: "",
  isAutoPlaying: false,
  setupCount: null,
  setSetupCount: (count) => set({ setupCount: count }),

  fetchState: async () => {
    const previous = get().state;
    try {
      const res = await fetchWithRetry("/api/game/state");
      if (!res.ok) {
        if (previous && IN_GAME_PHASES.has(previous.phase)) {
          console.warn("fetchState failed during active game; keeping previous state");
          return;
        }
        set({ state: EMPTY_START_STATE });
        return;
      }
      const data = (await res.json()) as GameState;
      set({ state: data });
    } catch (err) {
      console.warn("fetchState unavailable:", err);
      if (previous && IN_GAME_PHASES.has(previous.phase)) {
        return;
      }
      set({ state: EMPTY_START_STATE });
    }
  },

  resetGame: async (userRole = "预言家", playerCount = 6, gameMode = "humanVsAI", startImmediately = false) => {
    set({ isLoading: true, selectedCardId: null, userSpeechText: "" });
    try {
      const res = await postJson("/api/game/reset", { userRole, playerCount, gameMode, startImmediately });
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed to reset game:", err);
      set({ isLoading: false });
    }
  },

  submitUserSpeech: async () => {
    const { userSpeechText } = get();
    set({ isLoading: true });
    try {
      const res = await postJson("/api/game/action", { action: "SPEECH_SUBMIT", text: userSpeechText });
      const data = await res.json();
      set({ state: data, userSpeechText: "", selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to submit speech:", err);
      set({ isLoading: false });
    }
  },

  castVote: async () => {
    const { selectedCardId } = get();
    if (selectedCardId === null) return;
    set({ isLoading: true });
    try {
      const res = await postJson("/api/game/action", { action: "USER_VOTE", targetId: selectedCardId });
      const data = await res.json();
      set({ state: data, selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to cast vote:", err);
      set({ isLoading: false });
    }
  },

  simulateNextAI: async () => {
    set({ isLoading: true });
    try {
      const res = await postJson("/api/game/action", { action: "SIMULATE_NEXT_SPEAKER" });
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed to simulate speaker:", err);
      set({ isLoading: false });
    }
  },

  nightSkillAction: async (actionType, targetId, additional) => {
    set({ isLoading: true });
    try {
      const res = await postJson("/api/game/action", { action: actionType, targetId, ...additional });
      const data = await res.json();
      set({ state: data, selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to exert night action:", err);
      set({ isLoading: false });
    }
  },

  transitionToDebate: async () => {
    set({ isLoading: true });
    try {
      const res = await postJson("/api/game/action", { action: "TRANSITION_TO_DEBATE" });
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed executing transition:", err);
      set({ isLoading: false });
    }
  },

  exitGame: async () => {
    set({ isLoading: true, isAutoPlaying: false });
    try {
      const res = await postJson("/api/game/exit");
      const data = await res.json();
      set({ state: data, isLoading: false });
    } catch (err) {
      console.error("Failed executing exitGame:", err);
      set({ isLoading: false });
    }
  },

  setSelectedCardId: (id) => set({ selectedCardId: id }),
  setUserSpeechText: (text) => set({ userSpeechText: text }),
  toggleAutoPlay: () => set((state) => ({ isAutoPlaying: !state.isAutoPlaying }))
}));
