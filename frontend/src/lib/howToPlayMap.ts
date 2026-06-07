import type { BackendHowToPlayPageData, HowToPlayPageData } from "../api/types";

export function mapHowToPlayPage(
  raw: BackendHowToPlayPageData | null | undefined
): HowToPlayPageData {
  const sections = Array.isArray(raw?.sections)
    ? raw!.sections!.map((section) => ({
        title: section.heading,
        value: [section.body, ...(section.bullets ?? [])].filter(Boolean).join("\n"),
      }))
    : [];

  const phaseFlow = Array.isArray(raw?.phase_flow)
    ? raw!.phase_flow!.map((step) => ({
        phase: step.title,
        description: step.description,
        duration_hint: "",
      }))
    : [];

  const victoryConditions = Array.isArray(raw?.victory_conditions)
    ? raw!.victory_conditions!.map((block) => ({
        camp: block.camp,
        title: block.title,
        conditions: block.conditions ?? [],
      }))
    : [];

  return {
    title: raw?.title || "玩法说明",
    subtitle: raw?.summary || "标准狼人杀流程与平台操作说明",
    description: raw?.sections?.[0]?.body || raw?.summary || "",
    sections,
    phase_flow: phaseFlow,
    victory_conditions: victoryConditions,
  };
}
