import type {
  BackendHomePageData,
  BackendNavLink,
  BackendStatCard,
  HomePageData,
  RunSummary,
} from "../api/types";
import { mapRunRow } from "../utils/runRows";

function num(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function statValue(cards: BackendStatCard[], index: number): number {
  return num(cards[index]?.value);
}

function formatRunDate(value: string | null): string {
  if (!value) return "";
  return value.replace("T", " ").slice(0, 16);
}

function winnerText(camp: string | null): string {
  const normalized = (camp ?? "").toLowerCase();
  if (normalized.includes("wolf")) return "狼人胜";
  if (normalized.includes("villager") || normalized === "good") return "好人胜";
  if (normalized.includes("draw")) return "平局";
  return "进行中";
}

function mapRunHighlight(run: RunSummary, index: number): HomePageData["highlights"][number] {
  const resolved = mapRunRow(run).playerCount;
  const playerCount = resolved > 0 ? resolved : "?";
  const replayState = run.has_replay ? "可复盘" : "暂无复盘";
  return {
    id: run.run_id || `run-${index + 1}`,
    title: winnerText(run.winner_camp),
    summary: `#${run.run_id || "unknown"} · ${replayState}`,
    category: `${playerCount}人局`,
    date: formatRunDate(run.created_at),
  };
}

function mapQuickLink(link: BackendNavLink): HomePageData["quickLinks"][number] {
  return {
    label: link.title || link.key,
    path: link.path || "/",
    description: link.description ?? "",
  };
}

export function mapHomePage(raw: BackendHomePageData | null | undefined): HomePageData {
  const statsCards = Array.isArray(raw?.stats_cards) ? raw!.stats_cards! : [];
  const recentRuns = Array.isArray(raw?.recent_runs) ? raw!.recent_runs! : [];
  const quickActions = Array.isArray(raw?.quick_actions) ? raw!.quick_actions! : [];
  const activeGames = recentRuns.filter((run) => !run.winner_camp).length;

  return {
    title: raw?.hero?.title || "AI 狼人杀",
    subtitle: "观测后台",
    description:
      raw?.hero?.subtitle ||
      "多智能体狼人杀博弈平台，支持 AI 对局、复盘分析与模型表现对比。",
    welcomeMessage: "",
    stats: {
      activeGames,
      totalMatchesPlayed: statValue(statsCards, 0),
      onlineAIs: statValue(statsCards, 2),
      averageRating: String(statValue(statsCards, 3)),
    },
    highlights: recentRuns.map(mapRunHighlight),
    quickLinks: quickActions.map(mapQuickLink),
  };
}
