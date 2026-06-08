import { useGameStore } from "../store";
import { rosterToInsightPlayers, type InsightPlayer } from "../lib/insightMap";
import type { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";
import type { WolfCampMindV2 } from "../lib/godRoleIntel";

export interface GameInsight {
  beliefs: BeliefSnapshot[] | null;
  voteSnapshot: VoteIntentionSnapshot | null;
  players: InsightPlayer[];
  speakerSeat: number | null;
  wolfCampMinds: Record<number, WolfCampMindV2> | null;
}

/**
 * Live god-view insight, fed by the spectate SSE stream (store.connectSpectate).
 * runId is accepted for API compatibility; data comes from the active stream.
 */
export function useGameInsight(_runId: string | null): GameInsight {
  const beliefs = useGameStore((s) => s.insightBeliefs);
  const voteSnapshot = useGameStore((s) => s.insightVote);
  const speakerSeat = useGameStore((s) => s.insightSpeakerSeat);
  const wolfCampMinds = useGameStore((s) => s.insightWolfCampMinds);
  const roster = useGameStore((s) => s.spectateRoster);
  const statePlayers = useGameStore((s) => s.state?.players);

  const alive: Record<number, boolean> = {};
  (statePlayers ?? []).forEach((p) => { alive[p.id] = p.isAlive; });

  return {
    beliefs,
    voteSnapshot,
    players: rosterToInsightPlayers(roster, alive),
    speakerSeat,
    wolfCampMinds,
  };
}
