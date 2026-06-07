import type {
  BackendShareReplayData,
  ShareReplayPageData,
} from "../api/types";

/**
 * Pure mapping layer: backend `/api/v1/pages/share-replay` (ShareReplayPageData)
 * -> the front-end `ShareReplayPageData` consumed by SharePage.
 *
 * Mirrors `lib/replayMap.ts`: pure functions, defensive defaults. The seams it
 * reconciles:
 *  - mvp_winner uses snake_case (player_name/role_name) and has no `citation`;
 *  - winner_camp is lowercase ("werewolf"/"villager") but the card wants the
 *    "WOLVES"/"VILLAGERS" enum;
 *  - key_moments is a list of plain strings, not {timeLabel, desc} objects.
 */

/** "player_5" / "5" -> 5; non-numeric -> 0. */
function toSeatNumber(playerId: string | number | null | undefined): number {
  const digits = String(playerId ?? "").replace(/\D/g, "");
  const n = parseInt(digits, 10);
  return Number.isNaN(n) ? 0 : n;
}

function playerCountFromRunId(runId: string | null | undefined): number | null {
  if (!runId) return null;
  const m = runId.match(/(?:^|[-_])(\d+)p(?:[-_]|$)/i);
  if (m) return Number(m[1]);
  return null;
}

function normalizePlayerCountLine(
  line: string | null | undefined,
  runId: string | null | undefined,
  fallback: string,
): string {
  const text = (line ?? "").trim();
  if (text && !/^0\s*人/.test(text)) return text;
  const n = playerCountFromRunId(runId);
  if (n && n > 0) {
    const rest = text.replace(/^0\s*人局?/, `${n} 人局`);
    return rest || `${n} 人局`;
  }
  return text || fallback;
}

function normalizeStatsLine(
  statsLine: string | null | undefined,
  runId: string | null | undefined,
): string {
  return normalizePlayerCountLine(statsLine, runId, "对局复盘");
}

function normalizeShareSummary(
  shareSummary: string | null | undefined,
  runId: string | null | undefined,
): string {
  return normalizePlayerCountLine(shareSummary, runId, "");
}

/** backend lowercase camp -> front-end enum (default VILLAGERS). */
function toWinnerCamp(camp: string | null | undefined): "WOLVES" | "VILLAGERS" {
  const c = (camp ?? "").toString().toLowerCase();
  return c.includes("wolf") || c.includes("wolv") ? "WOLVES" : "VILLAGERS"; // "werewolf" & "wolves"
}

export function mapSharePage(
  raw: BackendShareReplayData | null | undefined,
): ShareReplayPageData {
  const r = raw ?? ({} as BackendShareReplayData);
  const mvp = r.mvp_winner ?? null;
  const shareSummary = normalizeShareSummary(r.share_summary, r.run_id);
  // The backend share payload carries no per-MVP citation; fall back to the most
  // telling line available so the share card's quote is never empty.
  const citation =
    (Array.isArray(r.key_moments) && r.key_moments.find((m) => !!m)) ||
    shareSummary ||
    "在关键回合左右了战局";
  return {
    share_title: r.share_title ?? "",
    share_summary: shareSummary,
    winner_camp: toWinnerCamp(r.winner_camp),
    mvp_winner: {
      playerName: mvp?.player_name ?? "",
      playerId: toSeatNumber(mvp?.player_id),
      role: mvp?.role_name ?? "",
      citation: String(citation),
    },
    key_moments: (Array.isArray(r.key_moments) ? r.key_moments : []).map((line) => ({
      timeLabel: "",
      desc: String(line ?? ""),
    })),
    highlight_players: (Array.isArray(r.highlight_players) ? r.highlight_players : []).map(
      (p) => ({
        playerName: p?.player_name ?? "",
        role: p?.role_name ?? "",
        badge: "",
        description: "",
      }),
    ),
    stats_line: normalizeStatsLine(r.stats_line, r.run_id),
  };
}
