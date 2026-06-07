import type { RunSummary } from "../api/types";

export type WinnerCamp = "GOOD" | "WEREWOLF" | "DRAW" | "UNKNOWN";

export interface RunRow {
  runId: string;
  winnerCamp: WinnerCamp;
  playerCount: number;
  createdAt: string;
  hasReplay: boolean;
}

export function mapRunRow(s: RunSummary): RunRow {
  // 真实后端发出小写阵营（"werewolf" / "villager"），而非
  // "GOOD"/"WEREWOLF" 标记；将好人阵营（villager）映射为 GOOD，使好人胜利不会显示为"未结算"
  const c = (s.winner_camp ?? "").toLowerCase();
  let winnerCamp: WinnerCamp = "UNKNOWN";
  if (c.includes("wolf") || c.includes("wolv")) winnerCamp = "WEREWOLF"; // "werewolf" & "wolves"
  else if (c === "good" || c.includes("villager")) winnerCamp = "GOOD";
  else if (c.includes("draw") || c.includes("平")) winnerCamp = "DRAW";
  return {
    runId: s.run_id,
    winnerCamp,
    playerCount: s.player_count ?? 0,
    createdAt: s.created_at ?? "",
    hasReplay: s.has_replay,
  };
}
