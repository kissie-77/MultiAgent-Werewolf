import type {
  BackendRoleDetailData,
  BackendRoleListItem,
  BackendRolesPageData,
  RoleDetail,
  RolePromptEntry,
  RoleSkillEntry,
  RoleSummary,
  RolesPageData,
} from "../api/types";

function campToAlignment(camp: string): RoleSummary["alignment"] {
  const normalized = (camp ?? "").toLowerCase();
  if (normalized.includes("wolf") || normalized === "werewolf") return "EVIL";
  if (normalized.includes("neutral")) return "NEUTRAL";
  return "GOOD";
}

function mapDifficulty(value: string | undefined): RoleSummary["difficulty"] {
  const upper = (value ?? "MEDIUM").toUpperCase();
  if (upper === "EASY" || upper === "HEAVY") return upper;
  return "MEDIUM";
}

function mapListItem(item: BackendRoleListItem): RoleSummary {
  return {
    key: item.key,
    name: item.runtime_name || item.key,
    chineseName: item.display_name,
    alignment: campToAlignment(item.camp),
    difficulty: mapDifficulty(item.difficulty),
    tagline: item.tagline || "",
    shortDesc: item.short_desc || "",
    promptCount: item.prompt_count ?? 0,
    skillCount: item.skill_count ?? 0,
    promptVersion: item.prompt_version || "v1",
    skillVersion: item.skill_version || "v1",
    promptRoleKey: item.prompt_role_key || "",
    hasNightAction: item.has_night_action ?? false,
  };
}

export function mapRolesPage(raw: BackendRolesPageData | null | undefined): RolesPageData {
  const camps = raw?.camps ?? {};
  const roles: RoleSummary[] = [];
  for (const items of Object.values(camps)) {
    if (!Array.isArray(items)) continue;
    for (const item of items) {
      roles.push(mapListItem(item));
    }
  }
  const campOrder = ["werewolf", "villager", "neutral"];
  roles.sort((a, b) => {
    const campA = Object.entries(camps).find(([, list]) => list?.some((r) => r.key === a.key))?.[0] ?? "";
    const campB = Object.entries(camps).find(([, list]) => list?.some((r) => r.key === b.key))?.[0] ?? "";
    const orderA = campOrder.indexOf(campA);
    const orderB = campOrder.indexOf(campB);
    if (orderA !== orderB) return (orderA === -1 ? 99 : orderA) - (orderB === -1 ? 99 : orderB);
    return a.chineseName.localeCompare(b.chineseName, "zh");
  });

  return {
    roles,
    camps: raw?.camps ?? {},
    campStats: raw?.camp_stats ?? {},
    introTitle: raw?.intro_title || raw?.title || "角色列表",
    introText:
      raw?.intro_text ||
      "二十二位命运刻印齐聚于此，点击卡牌查看规则权能、提升词库与技能库。",
    total: raw?.total ?? roles.length,
  };
}

function mapPromptEntry(entry: BackendRoleDetailData["prompt_library"][number]): RolePromptEntry {
  return {
    id: entry.id,
    category: entry.category,
    title: entry.title,
    content: entry.content,
    version: entry.version ?? "v1",
  };
}

function mapSkillEntry(entry: BackendRoleDetailData["skill_library"][number]): RoleSkillEntry {
  return {
    id: entry.id,
    title: entry.title,
    description: entry.description,
    status: entry.status ?? "active",
    weight: entry.weight ?? 1,
    version: entry.version ?? "v1",
  };
}

export function mapRoleDetail(raw: BackendRoleDetailData): RoleDetail {
  const base = mapListItem(raw);
  const abilities = Array.isArray(raw.abilities) ? raw.abilities : [];
  const strategies = Array.isArray(raw.strategies) ? raw.strategies : [];
  const promptLibrary = Array.isArray(raw.prompt_library)
    ? raw.prompt_library.map(mapPromptEntry)
    : [];
  const skillLibrary = Array.isArray(raw.skill_library)
    ? raw.skill_library.map(mapSkillEntry)
    : [];

  const loreParts = [raw.instruction, raw.victory_text].filter(Boolean);
  const relatedRoles = Array.isArray(raw.related_roles) ? raw.related_roles : [];

  return {
    ...base,
    lore: loreParts.join("\n\n"),
    promptLibrary,
    skillLibrary,
    skills: abilities.map((ability) => ({
      name: ability.name,
      description: ability.description,
      timing: (ability.timing?.toUpperCase() === "NIGHT"
        ? "NIGHT"
        : ability.timing?.toUpperCase() === "DAY"
          ? "DAY"
          : "PASSIVE") as "NIGHT" | "DAY" | "PASSIVE",
    })),
    strategies,
    relationships: relatedRoles.map((key) => ({
      targetRoleName: key,
      description: "同阵营关联角色，可组合出场于标准板子。",
      type: "ALLIED" as const,
    })),
    victoryText: raw.victory_text ?? "",
    suggestion: raw.suggestion ?? "",
    boardSizes: raw.board_sizes ?? [],
    promptVersion: raw.prompt_version || promptLibrary[0]?.version || "v1",
    skillVersion: raw.skill_version || skillLibrary[0]?.version || "v1",
  };
}
