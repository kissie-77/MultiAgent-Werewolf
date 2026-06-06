export interface BeliefCell {
  target_seat: number;
  wolf_probability: number;
  reason: string | null;
  note: string | null;
}

export interface BeliefSnapshot {
  round: number;
  phase: string;
  anchor: string;
  observer_id: string;
  observer_seat: number;
  vote_intention: { seat: number; reason: string };
  first_order: BeliefCell[];
}

export interface VoteEntry {
  player_id: string;
  seat: number;
  target_id: string | null;
  target_name: string | null;
  reason: string;
}

export interface Swing {
  player_id: string;
  player_name: string;
  from_seat: number;
  to_seat: number;
  to_target_name?: string;
}

export interface VoteIntentionSnapshot {
  round_number: number;
  phase: string;
  speaker_id: string;
  speaker_name: string;
  public_speech: string;
  before: Record<string, VoteEntry>;
  after: Record<string, VoteEntry>;
  swings: Swing[];
  swing_count: number;
  influence_score: number;
}
