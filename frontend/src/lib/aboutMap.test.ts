import { describe, expect, it } from "vitest";
import { mapAboutPage } from "./aboutMap";

describe("mapAboutPage", () => {
  it("maps backend about page fields", () => {
    const mapped = mapAboutPage({
      title: "AI 狼人杀介绍",
      summary: "多智能体平台",
      sections: [{ heading: "定位", body: "每个 Agent 独立决策", bullets: ["信息隔离"] }],
      platform_stats: { role_count: 22, config_count: 5 },
      tech_stack: ["FastAPI"],
      architecture_layers: [{ heading: "引擎", body: "GameEngine", bullets: [] }],
    });

    expect(mapped.subtitle).toBe("多智能体平台");
    expect(mapped.roleCount).toBe(22);
    expect(mapped.configCount).toBe(5);
    expect(mapped.sections[0].title).toBe("定位");
  });
});
