/** Nearest standard YAML used as resize base for arbitrary seat counts (4–20). */
const STANDARD_SIZES = [4, 6, 8, 12, 16] as const;

export const MIN_PLAYER_COUNT = 4;
export const MAX_PLAYER_COUNT = 20;

export function clampPlayerCount(count: number): number {
  return Math.max(MIN_PLAYER_COUNT, Math.min(MAX_PLAYER_COUNT, count));
}

/** Pick the closest ``standard-*p`` config; actual count goes in ``player_count``. */
export function nearestStandardConfigId(playerCount: number): string {
  const n = clampPlayerCount(playerCount);
  let pick: number = STANDARD_SIZES[0];
  for (const size of STANDARD_SIZES) {
    const dist = Math.abs(size - n);
    const pickDist = Math.abs(pick - n);
    if (dist < pickDist || (dist === pickDist && size > pick)) {
      pick = size;
    }
  }
  return `standard-${pick}p`;
}
