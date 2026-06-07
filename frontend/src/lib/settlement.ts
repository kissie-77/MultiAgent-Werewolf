import type { GameStatusResponse } from "../api/types";

/**
 * Settlement (game-over) helpers. Pure functions, defensive defaults.
 *
 * The backend flips `has_post_game` to true once `post_game_manifest.json`
 * lands on disk (services/runs.py `_scan_run_dir`). That is the gate the
 * settlement screen polls on before enabling the real replay link.
 */

/** Post-game artifacts are ready iff `has_post_game === true` (strict). */
export function isPostGameReady(
  status: GameStatusResponse | null | undefined,
): boolean {
  return status?.has_post_game === true;
}

/** Frontend route for the deep replay of a given run. */
export function replayPathFor(runId: string): string {
  return `/replay/${runId}`;
}
