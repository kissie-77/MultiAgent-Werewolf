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
 *  - backend `win_rate` is a 0..1 fraction, while the page renders `{win_rate}%`;
 *  - backend `avg_mvp` can be null, while the page calls `avg_mvp.toFixed(1)`.
 */

/** Coerce anything to a finite number; non-numeric / null / NaN -> 0. */
function num(x: unknown): number {
  const n = typeof x === "number" ? x : Number(x);
  return Number.isFinite(n) ? n : 0;
}

export function mapModelsPage(
  raw: BackendModelsPageData | null | undefined,
): ModelsPageData {
  const stats = Array.isArray(raw?.usage_stats) ? raw!.usage_stats! : [];
  const models: ModelUsageStat[] = stats.map((s) => ({
    model_id: s?.model_id ?? "",
    display_name: s?.display_name ?? s?.model_id ?? "",
    run_count: num(s?.run_count),
    win_rate: Math.round(num(s?.win_rate) * 100), // 0..1 fraction -> integer percent
    avg_mvp: num(s?.avg_mvp), // null -> 0 so the page's .toFixed(1) is safe
  }));
  return {
    models,
    introTitle: raw?.title || "模型排行榜",
    introText: "",
  };
}
