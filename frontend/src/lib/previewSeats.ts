import type { GameState } from "../types";
import { isLobbyPhase } from "./phaseStage";

export interface PreviewSeat {
  id: number;
  name: string;
  isAlive: boolean;
  isUser: boolean;
  isSpeaking: boolean;
}

/**
 * The seats ThreeCanvas should render.
 *
 * On the landing/setup screen `state` is still null so `phase` is undefined; we
 * treat that (and START_SCREEN/ROLE_CHOICE) as lobby and synthesize a preview
 * ring from `setupCount`. Otherwise we map the live players.
 */
export function buildPreviewSeats(args: {
  phase: GameState["phase"] | undefined;
  setupCount: number | null;
  players: GameState["players"];
  currentSpeakerId: number | null | undefined;
}): PreviewSeat[] {
  const { phase, setupCount, players, currentSpeakerId } = args;

  if (isLobbyPhase(phase) && setupCount !== null) {
    return Array.from({ length: setupCount }, (_, idx) => ({
      id: idx + 1,
      name: `席位 ${idx + 1}`,
      isAlive: true,
      isUser: idx === 0,
      isSpeaking: false,
    }));
  }

  return players.map((p) => ({
    id: p.id,
    name: p.name,
    isAlive: p.isAlive,
    isUser: p.isUser,
    isSpeaking: currentSpeakerId === p.id,
  }));
}
