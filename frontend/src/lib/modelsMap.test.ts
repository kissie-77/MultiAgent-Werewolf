import { describe, it, expect } from "vitest";
import { mapModelsPage } from "./modelsMap";
import type { BackendModelsPageData } from "../api/types";

const raw: BackendModelsPageData = {
  title: "模型排行榜",
  usage_stats: [
    { model_id: "deepseek-chat", display_name: "DeepSeek Chat", run_count: 4, win_rate: 0.5, avg_mvp: 31.2 },
    { model_id: "gpt-5", display_name: "GPT-5", run_count: 2, win_rate: null, avg_mvp: null },
  ],
  configs: [],
  by_provider: {},
  recommended_config_ids: [],
};

describe("mapModelsPage", () => {
  it("reads usage_stats into models", () => {
    const out = mapModelsPage(raw);
    expect(out.models).toHaveLength(2);
    expect(out.models[0].model_id).toBe("deepseek-chat");
    expect(out.models[0].display_name).toBe("DeepSeek Chat");
    expect(out.models[0].run_count).toBe(4);
  });

  it("scales win_rate fraction (0..1) to an integer percent", () => {
    expect(mapModelsPage(raw).models[0].win_rate).toBe(50);
  });

  it("defaults null win_rate / avg_mvp to 0 (page calls avg_mvp.toFixed)", () => {
    const m = mapModelsPage(raw).models[1];
    expect(m.win_rate).toBe(0);
    expect(m.avg_mvp).toBe(0);
    expect(m.avg_mvp.toFixed(1)).toBe("0.0");
  });

  it("carries avg_mvp through when present", () => {
    expect(mapModelsPage(raw).models[0].avg_mvp).toBeCloseTo(31.2);
  });

  it("derives intro title from backend title with a fallback", () => {
    expect(mapModelsPage(raw).introTitle).toBe("模型排行榜");
    expect(mapModelsPage({}).introTitle).toBe("模型排行榜");
    expect(typeof mapModelsPage({}).introText).toBe("string");
  });

  it("is defensive against missing usage_stats", () => {
    expect(mapModelsPage({}).models).toEqual([]);
    expect(mapModelsPage(null as unknown as BackendModelsPageData).models).toEqual([]);
  });
});
