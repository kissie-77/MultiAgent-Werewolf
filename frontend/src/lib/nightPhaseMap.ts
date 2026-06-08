import type {
  NightPhasePageData,
  NightStep,
  InvolvedRole,
  VisibilityRule,
} from "../api/types";

interface BackendNightStep {
  order: number;
  role_group: string;
  title: string;
  description: string;
}

interface BackendContentSection {
  heading: string;
  body: string;
  bullets?: string[];
}

/** Shape sent by the backend /api/v1/pages/night-phase (Pydantic NightPhasePageData). */
export interface BackendNightPhasePageData {
  title: string;
  summary?: string;
  sections?: BackendContentSection[];
  steps: BackendNightStep[];
  involved_roles: Record<string, string[]>;
  visibility_rules: BackendContentSection[];
  timeout_hints: Record<string, number>;
}

/**
 * Map the backend Pydantic shape to the front-end render shape.
 *
 * Backend: NightPhaseStep uses `order` / `role_group`; involved_roles is a dict;
 * visibility_rules are ContentSection (heading/body); timeout_hints is a dict.
 * Front-end: NightStep uses `seq`; involved_roles is InvolvedRole[];
 * visibility_rules is VisibilityRule[]; timeout_hints is string[].
 */
export function mapNightPhasePage(
  raw: BackendNightPhasePageData,
): NightPhasePageData {
  const steps: NightStep[] = (raw.steps ?? []).map((s) => ({
    seq: s.order,
    title: s.title,
    description: s.description,
  }));

  const involved_roles: InvolvedRole[] = Object.entries(
    raw.involved_roles ?? {},
  ).map(([name, actions]) => ({
    name,
    action_description: Array.isArray(actions)
      ? actions.join("；")
      : String(actions),
  }));

  const visibility_rules: VisibilityRule[] = (
    raw.visibility_rules ?? []
  ).map((r) => ({
    title: r.heading,
    rule: r.body,
  }));

  const timeout_hints: string[] = Object.entries(
    raw.timeout_hints ?? {},
  ).map(([key, value]) => `${key}: ${value}s`);

  return {
    title: raw.title || "黑夜行纪",
    subtitle: "夜间行动",
    description:
      raw.summary || "狼人杀夜晚阶段行动次第与黑盒蔽天规则。",
    sections: (raw.sections ?? []).map((s) => ({
      title: s.heading,
      value: s.body,
    })),
    steps,
    involved_roles,
    visibility_rules,
    timeout_hints,
  };
}
