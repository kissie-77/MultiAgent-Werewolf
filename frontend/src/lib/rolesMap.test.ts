import { describe, expect, it } from "vitest";
import { mapRoleDetail, mapRolesPage } from "./rolesMap";

describe("mapRolesPage", () => {
  it("flattens camp-grouped roles into display list", () => {
    const mapped = mapRolesPage({
      title: "角色列表",
      intro_title: "一览",
      intro_text: "介绍",
      total: 2,
      camps: {
        villager: [
          {
            key: "Seer",
            display_name: "预言家",
            camp: "villager",
            camp_label: "好人",
            victory_goal: "villager_eliminate_werewolves",
            prompt_count: 5,
            skill_count: 3,
            runtime_name: "Seer",
            tagline: "洞察黑夜",
            short_desc: "每晚查验",
            difficulty: "MEDIUM",
          },
        ],
        werewolf: [
          {
            key: "Werewolf",
            display_name: "狼人",
            camp: "werewolf",
            camp_label: "狼人",
            victory_goal: "werewolf_parity",
            prompt_count: 4,
            skill_count: 2,
          },
        ],
      },
    });

    expect(mapped.roles).toHaveLength(2);
    expect(mapped.roles.find((r) => r.key === "Seer")?.chineseName).toBe("预言家");
    expect(mapped.roles.find((r) => r.key === "Seer")?.alignment).toBe("GOOD");
    expect(mapped.roles.find((r) => r.key === "Werewolf")?.alignment).toBe("EVIL");
    expect(mapped.introTitle).toBe("一览");
  });
});

describe("mapRoleDetail", () => {
  it("maps prompt and skill libraries", () => {
    const mapped = mapRoleDetail({
      key: "Seer",
      display_name: "预言家",
      camp: "villager",
      camp_label: "好人",
      victory_goal: "villager_eliminate_werewolves",
      runtime_name: "Seer",
      instruction: "每晚查验一名玩家。",
      victory_text: "淘汰所有狼人。",
      prompt_library: [
        {
          id: "core_0",
          category: "核心原则",
          title: "核心原则 1",
          content: "查验是硬信息",
          version: "v1",
        },
      ],
      skill_library: [
        {
          id: "prophet_night_r1",
          title: "首夜查验",
          description: "优先验高置位",
          status: "active",
          weight: 0.9,
          version: "v1",
        },
      ],
      abilities: [{ name: "夜间行动", description: "每晚查验", timing: "NIGHT" }],
      strategies: ["谨慎报验"],
      related_roles: ["Witch"],
      board_sizes: [6, 12],
    });

    expect(mapped.promptLibrary).toHaveLength(1);
    expect(mapped.skillLibrary[0].id).toBe("prophet_night_r1");
    expect(mapped.skills[0].timing).toBe("NIGHT");
    expect(mapped.lore).toContain("每晚查验");
    expect(mapped.boardSizes).toEqual([6, 12]);
  });
});
