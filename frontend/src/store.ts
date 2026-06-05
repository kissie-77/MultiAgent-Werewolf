import { create } from "zustand";
import { GameState } from "./types";

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
  nightSkillAction: (actionType: "NIGHT_KILL" | "NIGHT_INSPECT" | "NIGHT_SAVED_OR_POISON", targetId: number, additional?: any) => Promise<void>;
  transitionToDebate: () => Promise<void>;
  exitGame: () => Promise<void>;
  setSelectedCardId: (id: number | null) => void;
  setUserSpeechText: (text: string) => void;
  toggleAutoPlay: () => void;
  setSetupCount: (count: number | null) => void;
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
    try {
      const res = await fetch("/api/game/state");
      if (!res.ok) {
        set({ state: EMPTY_START_STATE });
        return;
      }
      const data = await res.json();
      set({ state: data });
    } catch (err) {
      console.warn("Express mock unavailable, using START_SCREEN:", err);
      set({ state: EMPTY_START_STATE });
    }
  },

  resetGame: async (userRole = "预言家", playerCount = 6, gameMode = "humanVsAI", startImmediately = false) => {
    set({ isLoading: true, selectedCardId: null, userSpeechText: "" });
    try {
      const res = await fetch("/api/game/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userRole, playerCount, gameMode, startImmediately })
      });
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
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
    const { selectedCardId } = get();
    if (selectedCardId === null) return;
    set({ isLoading: true });
    try {
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "USER_VOTE", targetId: selectedCardId })
      });
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
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
    set({ isLoading: true });
    try {
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
    set({ isLoading: true });
    try {
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "TRANSITION_TO_DEBATE" })
      });
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
      const res = await fetch("/api/game/exit", {
        method: "POST"
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
  toggleAutoPlay: () => set((state) => ({ isAutoPlaying: !state.isAutoPlaying }))
}));
