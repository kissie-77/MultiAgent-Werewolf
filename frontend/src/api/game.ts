import { fetchPage } from "./client";

export interface GameSnapshot {
  phase: string | null;
  round_number: number;
  winner_camp: string | null;
  is_ended: boolean;
  sheriff_id: string | null;
  alive_count: number;
  dead_count: number;
  event_count: number;
}

export interface StartGameRequest {
  config_id?: string;
  participation?: string;
  rules?: string;
  player_count?: number;
  run_label?: string;
}

export interface StartGameResponse {
  run_id: string;
  source: string;
  status: string;
  config_id: string;
  status_path: string;
  replay_page_path: string;
  player_count: number | null;
}

export interface GameStatusResponse {
  run_id: string;
  source: string;
  status: string;
  snapshot: GameSnapshot | null;
  error: string | null;
  result_text: string | null;
  has_post_game: boolean;
  has_replay: boolean;
  post_game_status: string | null;
}

export interface ReplayEventItem {
  index: number;
  event_type: string;
  round_number: number;
  phase: string;
  message: string;
  timestamp: string | null;
}

export interface GamePageData {
  title: string;
  active_run: { run_id: string; status: string } | null;
  snapshot: GameSnapshot | null;
  recent_events: ReplayEventItem[];
  players: { seat: number; name: string; role_name: string | null; is_alive: boolean }[];
}

export function startGame(body: StartGameRequest) {
  return fetchPage<StartGameResponse>("/games/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchGameStatus(runId: string, source = "runs") {
  return fetchPage<GameStatusResponse>(`/games/${runId}/status?source=${source}`);
}

export function fetchGamePage(runId?: string) {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return fetchPage<GamePageData>(`/pages/game${query}`);
}

export function cancelGame(runId: string) {
  return fetchPage<{ run_id: string; status: string; message: string | null }>(
    `/games/${runId}/cancel`,
    { method: "POST" },
  );
}
