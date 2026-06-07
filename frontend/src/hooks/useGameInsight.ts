import { useGameStore } from "../store";
import { rosterToInsightPlayers, type InsightPlayer } from "../lib/insightMap";
import type { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";

export interface GameInsight {
  beliefs: BeliefSnapshot[] | null;
  voteSnapshot: VoteIntentionSnapshot | null;
  players: InsightPlayer[];
}

/**
 * God-view insight from live SSE or log-replay timeline (store.connectSpectate).
 * runId is accepted for API compatibility; data comes from the active session.
 */
export function useGameInsight(_runId: string | null): GameInsight {
  const beliefs = useGameStore((s) => s.insightBeliefs);
  const voteSnapshot = useGameStore((s) => s.insightVote);
  const roster = useGameStore((s) => s.spectateRoster);
  const statePlayers = useGameStore((s) => s.state?.players);

  const alive: Record<number, boolean> = {};
  (statePlayers ?? []).forEach((p) => { alive[p.id] = p.isAlive; });

  return { beliefs, voteSnapshot, players: rosterToInsightPlayers(roster, alive) };
}
