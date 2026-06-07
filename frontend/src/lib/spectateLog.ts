import type { BackendReplayEventItem } from "../api/types";
import type { SseEvent } from "./gameReducer";
import { initialSpectateState, reduceEvent } from "./gameReducer";
import type { GameState } from "../types";

const SPEECH_EVENTS = new Set(["player_speech", "player_discussion"]);
const INSIGHT_EVENTS = new Set(["belief_snapshot", "vote_intention_snapshot"]);

/** Map a replay timeline row (from events.jsonl via pages/replay) into reducer input. */
export function logEventToSse(ev: BackendReplayEventItem): SseEvent {
  return {
    event_type: ev.event_type,
    round_number: ev.round_number,
    phase: ev.phase,
    message: ev.message,
    data: ev.data,
  };
}

/** Seed spectate state from roster before streaming log events. */
export function initialStateWithRoster(roster?: SseEvent["roster"]): GameState {
  let state = initialSpectateState();
  if (roster?.length) {
    state = reduceEvent(state, { event_type: "snapshot", roster });
  }
  return state;
}

/** Milliseconds to wait before applying the next replay row (tuned for readability). */
export function delayForLogEvent(ev: BackendReplayEventItem): number {
  if (SPEECH_EVENTS.has(ev.event_type)) return 900;
  if (INSIGHT_EVENTS.has(ev.event_type)) return 250;
  if (ev.event_type === "game_ended") return 500;
  if (ev.event_type === "phase_changed") return 350;
  return 70;
}

/** Fold a full on-disk event log into a spectate GameState. */
export function hydrateStateFromLogEvents(
  events: BackendReplayEventItem[],
  roster?: SseEvent["roster"],
): GameState {
  let state = initialStateWithRoster(roster);
  for (const row of events) {
    state = reduceEvent(state, logEventToSse(row));
  }
  return state;
}

export interface LogReplayInsightPatch {
  beliefs?: import("../api/insightTypes").BeliefSnapshot[] | null;
  vote?: import("../api/insightTypes").VoteIntentionSnapshot | null;
}

export interface LogReplayDrainOptions {
  events: BackendReplayEventItem[];
  initial: GameState;
  isPaused: () => boolean;
  onStep: (state: GameState, insight?: LogReplayInsightPatch) => void;
  onComplete: () => void;
  mapBelief: (data: Record<string, unknown> | undefined) => import("../api/insightTypes").BeliefSnapshot[] | null;
  mapVote: (data: Record<string, unknown> | undefined) => import("../api/insightTypes").VoteIntentionSnapshot | null;
}

/** Apply replay timeline one event at a time; returns a stop handle for teardown. */
export function startLogReplayDrain(opts: LogReplayDrainOptions): { stop: () => void } {
  let idx = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let current = opts.initial;

  const stop = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const tick = () => {
    if (opts.isPaused()) {
      timer = setTimeout(tick, 250);
      return;
    }
    if (idx >= opts.events.length) {
      stop();
      opts.onComplete();
      return;
    }
    const row = opts.events[idx];
    idx += 1;
    current = reduceEvent(current, logEventToSse(row));
    const insight: LogReplayInsightPatch = {};
    if (row.event_type === "belief_snapshot") {
      insight.beliefs = opts.mapBelief(row.data);
    } else if (row.event_type === "vote_intention_snapshot") {
      insight.vote = opts.mapVote(row.data);
    }
    opts.onStep(current, Object.keys(insight).length ? insight : undefined);
    timer = setTimeout(tick, delayForLogEvent(row));
  };

  timer = setTimeout(tick, 120);
  return { stop };
}
