import type { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";

export interface RosterEntry {
  seat: number;
  name: string;
  role: string;
  camp?: string | null;
  is_alive?: boolean;
}

export interface InsightPlayer {
  seat: number;
  id: string;
  name: string;
  role: string;
  camp: string;
  alive: boolean;
}

/** belief_snapshot event.data.snapshots[] are already BeliefSnapshot-shaped records. */
export function mapBeliefEvent(data: any): BeliefSnapshot[] {
  const snaps = data?.snapshots;
  return Array.isArray(snaps) ? (snaps as BeliefSnapshot[]) : [];
}

/** vote_intention_snapshot event.data ~= VoteIntentionSnapshot; influence_score is not
 *  emitted by the backend record, so derive a default from swing_count. */
export function mapVoteEvent(data: any): VoteIntentionSnapshot {
  const swings = Array.isArray(data?.swings) ? data.swings : [];
  const swingCount = typeof data?.swing_count === "number" ? data.swing_count : swings.length;
  return {
    round_number: data?.round_number ?? 0,
    phase: data?.phase ?? "",
    speaker_id: data?.speaker_id ?? "",
    speaker_name: data?.speaker_name ?? "",
    public_speech: data?.public_speech ?? "",
    before: data?.before ?? {},
    after: data?.after ?? {},
    swings,
    swing_count: swingCount,
    influence_score: typeof data?.influence_score === "number" ? data.influence_score : swingCount * 10,
  };
}

/** Build insight players from the god roster (for camp/role) + live alive status (by seat). */
export function rosterToInsightPlayers(
  roster: RosterEntry[] | null,
  alive: Record<number, boolean>,
): InsightPlayer[] {
  if (!roster) return [];
  return roster.map((r) => ({
    seat: r.seat,
    id: `player_${r.seat}`,
    name: r.name,
    role: r.role,
    camp: r.camp ?? "unknown",
    alive: alive[r.seat] ?? r.is_alive !== false,
  }));
}
