import { describe, expect, it } from "vitest";
import { mapHowToPlayPage } from "./howToPlayMap";

describe("mapHowToPlayPage", () => {
  it("maps backend snake_case fields to page shape", () => {
    const mapped = mapHowToPlayPage({
      title: "玩法说明",
      summary: "流程介绍",
      sections: [
        {
          heading: "游戏目标",
          body: "争取阵营胜利",
          bullets: ["好人淘汰狼人"],
        },
      ],
      phase_flow: [
        {
          order: 1,
          phase_key: "night",
          title: "夜晚",
          description: "私密行动",
        },
      ],
      victory_conditions: [
        {
          camp: "好人阵营",
          title: "好人胜利",
          conditions: ["淘汰所有狼人"],
        },
      ],
    });

    expect(mapped.subtitle).toBe("流程介绍");
    expect(mapped.phase_flow[0].phase).toBe("夜晚");
    expect(mapped.victory_conditions[0].conditions).toContain("淘汰所有狼人");
    expect(mapped.sections[0].title).toBe("游戏目标");
  });
});
