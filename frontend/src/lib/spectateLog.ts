import type { BackendReplayEventItem } from "../api/types";
import type { SseEvent } from "./gameReducer";
import { initialSpectateState, reduceEvent } from "./gameReducer";
import type { GameState } from "../types";

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

/** Fold a full on-disk event log into a spectate GameState. */
export function hydrateStateFromLogEvents(
  events: BackendReplayEventItem[],
  roster?: SseEvent["roster"],
): GameState {
  let state = initialSpectateState();
  if (roster?.length) {
    state = reduceEvent(state, { event_type: "snapshot", roster });
  }
  for (const row of events) {
    state = reduceEvent(state, logEventToSse(row));
  }
  return state;
}
