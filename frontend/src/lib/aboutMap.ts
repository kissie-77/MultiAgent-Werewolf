import type { AboutPageData, BackendAboutPageData } from "../api/types";

export function mapAboutPage(raw: BackendAboutPageData | null | undefined): AboutPageData {
  const sections = Array.isArray(raw?.sections)
    ? raw!.sections!.map((s) => ({
        title: s.heading,
        value: [s.body, ...(s.bullets ?? [])].filter(Boolean).join("\n"),
      }))
    : [];

  const layers = Array.isArray(raw?.architecture_layers) ? raw!.architecture_layers! : [];
  const designPrinciples = layers.map((layer) => {
    const bullets = layer.bullets?.length ? `：${layer.bullets.join("；")}` : "";
    return `${layer.heading}${bullets || (layer.body ? `：${layer.body}` : "")}`;
  });

  return {
    title: raw?.title || "AI 狼人杀",
    subtitle: raw?.summary || "多智能体狼人杀博弈平台",
    description: raw?.sections?.[0]?.body || raw?.summary || "",
    sections,
    design_principles: designPrinciples,
    roleCount: typeof raw?.platform_stats?.role_count === "number" ? raw.platform_stats.role_count : undefined,
    configCount: typeof raw?.platform_stats?.config_count === "number" ? raw.platform_stats.config_count : undefined,
    techStack: raw?.tech_stack ?? [],
    platformStats: raw?.platform_stats ?? {},
  };
}
