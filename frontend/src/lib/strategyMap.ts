import type { StrategyPageData, PhaseTip, RoleTipByCamp } from "../api/types";

interface BackendStrategyTip {
  role_key: string | null;
  title: string;
  content: string;
  tags: string[];
}

/** Shape sent by the backend /api/v1/pages/strategy (Pydantic StrategyPageData). */
export interface BackendStrategyPageData {
  title: string;
  general_tips: BackendStrategyTip[];
  phase_tips: BackendStrategyTip[];
  role_tips: BackendStrategyTip[];
  role_tips_by_camp: Record<string, BackendStrategyTip[]>;
  post_game_links?: unknown[];
}

/**
 * Map the backend Pydantic shape to the front-end render shape.
 *
 * Backend fields are StrategyTip objects; the front-end page reads
 * general_tips as strings, phase_tips as PhaseTip[], and expects
 * role_tips_by_camp to be an array (not a dict).
 */
export function mapStrategyPage(raw: BackendStrategyPageData): StrategyPageData {
  // general_tips: object[] → string[]
  const general_tips = (raw.general_tips ?? []).map(
    (t) => `【${t.title}】${t.content}`,
  );

  // phase_tips: StrategyTip[] → PhaseTip[]
  const phase_tips: PhaseTip[] = (raw.phase_tips ?? []).map((t) => ({
    phase: t.title,
    tips: [t.content],
  }));

  // role_tips: StrategyTip[] → RoleTip[]
  const role_tips_map = new Map<string, string[]>();
  for (const t of raw.role_tips ?? []) {
    const role = t.role_key || t.title || "未知";
    if (!role_tips_map.has(role)) role_tips_map.set(role, []);
    role_tips_map.get(role)!.push(t.content);
  }
  const role_tips = Array.from(role_tips_map.entries()).map(
    ([role, tips]) => ({ role, tips }),
  );

  // role_tips_by_camp: dict → RoleTipByCamp[]
  const role_tips_by_camp: RoleTipByCamp[] = Object.entries(
    raw.role_tips_by_camp ?? {},
  ).map(([camp, tips]) => ({
    camp,
    tips: tips.map((t) => `【${t.title}】${t.content}`),
  }));

  return {
    title: raw.title || "智斗秘卷",
    subtitle: "战术手册",
    description: "全智能圆桌战术册 — 根据二十二刻印权能与对局模式提供微操建议。",
    sections: [],
    general_tips,
    phase_tips,
    role_tips,
    role_tips_by_camp,
  };
}
