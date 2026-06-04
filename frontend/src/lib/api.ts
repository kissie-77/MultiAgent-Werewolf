import { ControlRequest, ControlResponse, GamePhase, GameStateResponse } from "../types";

export const API = "/api/v1";

function unwrap<T>(json: unknown): T {
  return (json && typeof json === "object" && "data" in (json as Record<string, unknown>)
    ? (json as { data: T }).data
    : json) as T;
}

export function streamUrl(runId: string): string {
  return `${API}/games/${runId}/stream`;
}

export async function fetchState(runId: string): Promise<GameStateResponse> {
  const res = await fetch(`${API}/games/${runId}/state`);
  if (!res.ok) throw new Error(`state failed: HTTP ${res.status}`);
  return unwrap<GameStateResponse>(await res.json());
}

export async function postControl(runId: string, req: ControlRequest): Promise<ControlResponse> {
  const res = await fetch(`${API}/games/${runId}/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`control failed: HTTP ${res.status}`);
  return unwrap<ControlResponse>(await res.json());
}

// Single authoritative night/day predicate — replaces every component string-match.
export function isNightPhase(phase: GamePhase | null | undefined): boolean {
  return phase === GamePhase.night || phase === GamePhase.setup;
}
