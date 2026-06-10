import { describe, it, expect } from "vitest";
import { selectOverallStats, LOW_SAMPLE_THRESHOLD } from "./modelOverall";
import type { ModelUsageStat } from "../api/types";

const stat = (over: Partial<ModelUsageStat>): ModelUsageStat => ({
  model_id: "m",
  display_name: "M",
  role_name: null,
  run_count: 10,
  win_rate: 50,
  avg_mvp: 30,
  ...over,
});

describe("selectOverallStats", () => {
  it("只保留不带角色的聚合条目", () => {
    const rows = selectOverallStats([
      stat({ model_id: "a", display_name: "A（狼人）", role_name: "Werewolf" }),
      stat({ model_id: "a", display_name: "A" }),
      stat({ model_id: "b", display_name: "B（女巫）", role_name: "Witch" }),
    ]);
    expect(rows.map((r) => r.display_name)).toEqual(["A"]);
  });

  it("默认按胜率降序,胜率相同按对局数降序", () => {
    const rows = selectOverallStats([
      stat({ model_id: "a", win_rate: 25, run_count: 4 }),
      stat({ model_id: "b", win_rate: 50, run_count: 2 }),
      stat({ model_id: "c", win_rate: 25, run_count: 59 }),
    ]);
    expect(rows.map((r) => r.model_id)).toEqual(["b", "c", "a"]);
  });

  it("可切换为按对局数排序", () => {
    const rows = selectOverallStats(
      [
        stat({ model_id: "a", run_count: 4 }),
        stat({ model_id: "b", run_count: 59 }),
      ],
      "run_count",
    );
    expect(rows.map((r) => r.model_id)).toEqual(["b", "a"]);
  });

  it("空字符串 role_name 也视为聚合条目", () => {
    const rows = selectOverallStats([stat({ role_name: "" })]);
    expect(rows).toHaveLength(1);
  });

  it("空输入返回空数组", () => {
    expect(selectOverallStats([])).toEqual([]);
  });

  it("暴露样本少阈值常量", () => {
    expect(LOW_SAMPLE_THRESHOLD).toBe(3);
  });
});
