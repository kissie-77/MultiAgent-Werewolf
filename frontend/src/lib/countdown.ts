/**
 * Remaining whole seconds for a human-decision deadline.
 *
 * `deadlineSec` is the duration (in seconds) the backend granted the seat — it
 * travels on the `awaiting_input` event as `deadline`. `startedAtMs` is when the
 * panel first showed the request; `nowMs` is the current clock. The result is
 * clamped to `[0, deadlineSec]`, and is `0` for a missing / non-positive /
 * non-finite deadline (so the UI simply shows no countdown).
 */
export function remainingSeconds(
  deadlineSec: number,
  startedAtMs: number,
  nowMs: number,
): number {
  if (!Number.isFinite(deadlineSec) || deadlineSec <= 0) return 0;
  const elapsedSec = Math.max(0, (nowMs - startedAtMs) / 1000);
  return Math.max(0, Math.ceil(deadlineSec - elapsedSec));
}
