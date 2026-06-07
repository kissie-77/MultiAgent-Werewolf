import type { HomePageData } from "../api/types";

/**
 * Pure mapping layer: backend `GET /api/v1/pages/home` -> the front-end
 * `HomePageData` shape consumed by HomePage.
 *
 * Mirrors `lib/replayMap.ts` / `lib/modelsMap.ts`: pure functions, defensive
 * defaults, snake->camel. The backend payload is `{hero, stats_cards,
 * recent_runs, quick_actions, ...}` while HomePage expects `{title, subtitle,
 * description, stats:{...}, highlights[], ...}`. Without this mapper HomePage
 * dereferenced `data.stats.activeGames` on an undefined `stats` and white-screened.
 */

interface BackendHomeHero {
  title?: string | null;
  subtitle?: string | null;
  cta_label?: string | null;
  cta_path?: string | null;
}

interface BackendStatCard {
  label?: string | null;
  value?: number | string | null;
  unit?: string | null;
  hint?: string | null;
}

interface BackendRecentRun {
  run_id?: string | null;
  created_at?: string | null;
  player_count?: number | null;
  winner_camp?: string | null;
  has_replay?: boolean | null;
}

interface BackendQuickAction {
  key?: string | null;
  title?: string | null;
  path?: string | null;
  description?: string | null;
}

export interface BackendHomePageData {
  hero?: BackendHomeHero | null;
  stats_cards?: BackendStatCard[] | null;
  recent_runs?: BackendRecentRun[] | null;
  quick_actions?: BackendQuickAction[] | null;
}

/** Coerce anything to a finite number; non-numeric / NaN -> 0. */
function toNum(x: unknown): number {
  const n = typeof x === "number" ? x : Number(x);
  return Number.isFinite(n) ? n : 0;
}

/** Value of the first stat card whose label contains any of `keys` (default 0). */
function statValue(cards: BackendStatCard[], keys: string[], dflt = 0): number {
  const card = cards.find((c) => keys.some((k) => (c?.label ?? "").includes(k)));
  return card ? toNum(card.value) : dflt;
}

/** lowercase backend camp -> human-readable zh label (defensive). */
function campLabel(camp: string | null | undefined): string {
  const c = (camp ?? "").toString().toLowerCase();
  if (c.includes("wolf") || c.includes("wolv")) return "狼人胜";
  if (c.includes("villager") || c === "good") return "好人胜";
  return "未结算";
}

export function mapHomePage(raw: BackendHomePageData | null | undefined): HomePageData {
  const d = raw ?? {};
  const hero = d.hero ?? {};
  const cards = Array.isArray(d.stats_cards) ? d.stats_cards : [];
  const runs = Array.isArray(d.recent_runs) ? d.recent_runs : [];
  const actions = Array.isArray(d.quick_actions) ? d.quick_actions : [];

  // 后端统计卡片（历史对局/角色数量/可用配置/含复盘）与前端
  // 四个槽位不同；按标签子串尽力映射，缺失/重命名卡片不会导致渲染崩溃
  const rating = statValue(cards, ["评分", "胜率"]);

  return {
    title: hero.title ?? "AI 狼人杀",
    subtitle: hero.subtitle ?? "",
    description: hero.subtitle ?? "",
    welcomeMessage: hero.title ?? "",
    stats: {
      totalMatchesPlayed: statValue(cards, ["对局", "历史"]),
      activeGames: statValue(cards, ["进行", "存续", "活跃", "复盘"]),
      onlineAIs: statValue(cards, ["角色", "模型", "智能", "配置"]),
      averageRating: rating > 0 ? String(rating) : "—",
    },
    highlights: runs.map((r, i) => ({
      id: r?.run_id ?? String(i),
      title: `${toNum(r?.player_count) || "?"} 人局 · ${campLabel(r?.winner_camp)}`,
      summary: `对局 ${r?.run_id ?? ""}${r?.has_replay ? "（含复盘）" : ""}`.trim(),
      category: campLabel(r?.winner_camp),
      date: r?.created_at ?? "",
    })),
    quickLinks: actions.map((a) => ({
      label: a?.title ?? "",
      path: a?.path ?? "/",
      description: a?.description ?? "",
    })),
  };
}
