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

export interface ExposureCell {
  observer_seat: number;
  suspicion: number;
  reason: string | null;
}

/** after_speech -> 发言人的 observer_seat；initial/空 speaker_id/找不到 -> null。 */
export function mapSpeakerSeat(data: any): number | null {
  const sid = data?.speaker_id;
  if (!sid) return null;
  const snaps = Array.isArray(data?.snapshots) ? data.snapshots : [];
  const self = snaps.find((s: any) => s?.observer_id === sid);
  return typeof self?.observer_seat === "number" ? self.observer_seat : null;
}

/** 取发言人那条 snapshot 的 second_order，按 suspicion 降序；无发言人/无 B2 -> []。 */
export function selectExposureRow(
  beliefs: BeliefSnapshot[] | null,
  speakerSeat: number | null,
): ExposureCell[] {
  if (!beliefs || speakerSeat == null) return [];
  const me = beliefs.find((b) => b.observer_seat === speakerSeat);
  const rows = me?.second_order ?? [];
  return [...rows]
    .map((r) => ({ observer_seat: r.observer_seat, suspicion: r.suspects_me_as_wolf, reason: r.reason }))
    .sort((a, b) => b.suspicion - a.suspicion);
}
