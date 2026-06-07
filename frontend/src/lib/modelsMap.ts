import type {
  BackendModelsPageData,
  ModelsPageData,
  ModelUsageStat,
} from "../api/types";

/**
 * Pure mapping layer: backend `/api/v1/pages/models` (ModelListPageData) ->
 * the front-end `ModelsPageData` consumed by ModelsPage.
 *
 * Mirrors `lib/replayMap.ts`: pure functions, defensive defaults. The seams it
 * reconciles:
 *  - the page reads `data.models`, but the backend sends `usage_stats`;
 *  - backend `win_rate` may be a 0..1 fraction OR already a 0..100 percent;
 *    we detect which by checking magnitude (>1 means already percent);
 *  - backend `avg_mvp` can be null, while the page calls `avg_mvp.toFixed(1)`.
 */

/** Coerce anything to a finite number; non-numeric / null / NaN -> 0. */
function num(x: unknown): number {
  const n = typeof x === "number" ? x : Number(x);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Normalise win_rate to 0..100 integer percent.
 * Handles both 0..1 fraction (e.g. 0.65) and 0..100 percent (e.g. 65.2).
 */
function toWinRate(x: unknown): number {
  const v = num(x);
  // If value is already in 0..100 range, round it; if it's a 0..1 fraction, scale up.
  return v > 1 ? Math.round(v) : Math.round(v * 100);
}

export function mapModelsPage(
  raw: BackendModelsPageData | null | undefined,
): ModelsPageData {
  const stats = Array.isArray(raw?.usage_stats) ? raw!.usage_stats! : [];
  const models: ModelUsageStat[] = stats.map((s) => ({
    model_id: s?.model_id ?? "",
    display_name: s?.display_name ?? s?.model_id ?? "",
    run_count: num(s?.run_count),
    win_rate: toWinRate(s?.win_rate), // robust: handles both 0..1 and 0..100
    avg_mvp: num(s?.avg_mvp), // null -> 0 so the page's .toFixed(1) is safe
  }));
  return {
    models,
    introTitle: raw?.title || "模型排行榜",
    introText: "",
  };
}
