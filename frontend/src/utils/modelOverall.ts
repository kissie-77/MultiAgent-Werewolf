import type { ModelUsageStat } from "../api/types";

export type OverallSortKey = "win_rate" | "run_count";

/** 对局数低于该阈值的条目在 UI 上标记「样本少」 */
export const LOW_SAMPLE_THRESHOLD = 3;

/**
 * 从模型页数据中取「不区分角色」的聚合条目并排序。
 * 后端 aggregate_model_usage 对每个模型同时产出 (model, role) 与 model 两个粒度,
 * 这里只保留 role_name 为空的聚合粒度(null / undefined / "")。
 */
export function selectOverallStats(
  models: ModelUsageStat[],
  sortKey: OverallSortKey = "win_rate",
): ModelUsageStat[] {
  return models
    .filter((m) => !m.role_name)
    .sort(
      (a, b) =>
        b[sortKey] - a[sortKey] ||
        b.run_count - a.run_count ||
        a.display_name.localeCompare(b.display_name),
    );
}
