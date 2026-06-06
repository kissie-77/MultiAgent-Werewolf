import type { GameState, Player } from "../types";
import type { ReplayPageData } from "../api/types";

/**
 * Game-over data resolution for GameOverPanel.
 *
 * Fixes two real bugs the human-vs-AI E2E surfaced:
 *  - BUG-1: the seat SSE path never populates `gameState.players`, so the old
 *    client `calculateMVP` returned `undefined` and `mvp.role` threw, white-
 *    screening the whole app. Every resolver here is null-safe.
 *  - BUG-7: the client MVP heuristic disagreed with the backend (it showed a
 *    *wolf* as MVP on a good-guy win). When backend post-game data is present we
 *    prefer it (it is the authoritative `mvp_scores.json` ranking) over the
 *    client recompute.
 */

const WOLF_ROLES = new Set([
  // Chinese display names
  "狼人", "狼王", "白狼", "狼美人", "守卫狼", "隐狼", "血月使徒", "梦魇狼",
  // English roster role names
  "Werewolf", "AlphaWolf", "WhiteWolf", "WolfBeauty", "GuardianWolf", "HiddenWolf",
  "BloodMoonApostle", "NightmareWolf",
]);

export function isWolfRole(role: string): boolean {
  return WOLF_ROLES.has(role);
}

export interface MvpView {
  id: number;
  name: string;
  role: string;
  isAlive: boolean;
  isUser: boolean;
  speechCount: number;
}

export interface BoardPlayer {
  id: number;
  name: string;
  role: string;
  isAlive: boolean;
  isUser: boolean;
  statusNotes: string;
}

function cleanName(name: string | null | undefined): string {
  return String(name ?? "").replace(/\(.*?\)/g, "").trim();
}

function speechCountOf(gameState: GameState | null | undefined, id: number): number {
  const logs = gameState?.speechLogs ?? [];
  return logs.filter((l) => l.playerId === id).length;
}

/**
 * Legacy client-side MVP heuristic — crash-proofed: an empty roster (the seat
 * SSE path) returns null instead of `undefined`, so callers never deref it.
 * Kept only as the fallback for local games that have a populated roster.
 */
export function clientMvp(gameState: GameState | null | undefined): Player | null {
  const players = gameState?.players ?? [];
  if (players.length === 0) return null;
  const isGoodWin = gameState?.winner === "VILLAGERS";

  const scores = players.map((player) => {
    let score = 0;
    const wolf = isWolfRole(player.role);
    if (isGoodWin && !wolf) score += 45;
    else if (!isGoodWin && wolf) score += 45;
    if (player.isAlive) score += 25;
    score += speechCountOf(gameState, player.id) * 6;
    if (player.role === "预言家") {
      if (gameState?.seerVerifiedTarget != null) score += 20;
      if (gameState?.seerVerificationResult === "WEREWOLF") score += 35;
    } else if (player.role === "女巫") {
      if (gameState?.witchSaved) score += 30;
      if (gameState?.witchPoisonedTarget != null) score += 30;
    } else if (player.role === "猎人") {
      if (!player.isAlive) score += 20;
    } else if (wolf) {
      if (gameState?.wolfKilledTarget != null) score += 20;
      if (player.isAlive && !isGoodWin) score += 20;
    }
    score += (player.id * 2.3) % 7;
    return { player, score };
  });

  scores.sort((a, b) => b.score - a.score);
  return scores[0]?.player ?? null;
}

/**
 * The MVP to display: prefer the backend ranking (authoritative), else the
 * crash-proof client heuristic, else null. Never throws.
 */
export function resolveMvpView(
  backend: ReplayPageData | null | undefined,
  gameState: GameState | null | undefined,
  userSeat: number | null,
): MvpView | null {
  const ranking = backend?.mvp_ranking;
  if (Array.isArray(ranking) && ranking.length > 0) {
    const top = ranking.find((m) => m?.isMvp) ?? ranking[0];
    const sc = (backend?.scores ?? []).find((s) => s.playerId === top.playerId);
    return {
      id: top.playerId,
      name: cleanName(top.playerName) || `玩家${top.playerId}`,
      role: top.role || sc?.role || "未知",
      isAlive: sc ? sc.isAlive : true,
      isUser: userSeat != null && top.playerId === userSeat,
      speechCount: speechCountOf(gameState, top.playerId),
    };
  }
  const cm = clientMvp(gameState);
  if (!cm) return null;
  return {
    id: cm.id,
    name: cleanName(cm.name) || `玩家${cm.id}`,
    role: cm.role,
    isAlive: cm.isAlive,
    isUser: cm.isUser,
    speechCount: speechCountOf(gameState, cm.id),
  };
}

/** The full board reveal: prefer backend scores, else the client roster, else []. */
export function resolveBoard(
  backend: ReplayPageData | null | undefined,
  clientPlayers: Player[] | null | undefined,
  userSeat: number | null,
): BoardPlayer[] {
  const scores = backend?.scores;
  if (Array.isArray(scores) && scores.length > 0) {
    return scores.map((s) => ({
      id: s.playerId,
      name: cleanName(s.playerName) || `玩家${s.playerId}`,
      role: s.role || "未知",
      isAlive: s.isAlive,
      isUser: userSeat != null && s.playerId === userSeat,
      statusNotes: "",
    }));
  }
  return (clientPlayers ?? []).map((p) => ({
    id: p.id,
    name: p.name,
    role: p.role,
    isAlive: p.isAlive,
    isUser: p.isUser,
    statusNotes: p.statusNotes,
  }));
}

/** Did the good camp win? Prefer backend winner_camp, else the client winner. */
export function resolveWinnerIsGood(
  backend: ReplayPageData | null | undefined,
  gameState: GameState | null | undefined,
): boolean {
  const camp = backend?.run?.winner_camp;
  if (camp === "VILLAGERS") return true;
  if (camp === "WOLVES") return false;
  return gameState?.winner === "VILLAGERS";
}
