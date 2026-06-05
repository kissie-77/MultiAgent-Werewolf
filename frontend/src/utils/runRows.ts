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
  const wc = (s.winner_camp ?? "").toUpperCase();
  const winnerCamp: WinnerCamp =
    wc === "GOOD" || wc === "WEREWOLF" || wc === "DRAW" ? (wc as WinnerCamp) : "UNKNOWN";
  return {
    runId: s.run_id,
    winnerCamp,
    playerCount: s.player_count ?? 0,
    createdAt: s.created_at ?? "",
    hasReplay: s.has_replay,
  };
}
