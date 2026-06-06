const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/+$/, "");

export type StreamView = "god" | "seat";

/** Build the SSE stream URL for a run. Relative by default (Vite proxy / nginx). */
export function streamUrl(
  runId: string,
  view: StreamView = "god",
  seat?: number,
  token?: string,
): string {
  const params = new URLSearchParams({ view });
  if (view === "seat" && seat != null) params.set("seat", String(seat));
  if (token) params.set("token", token);
  return `${API_BASE}/api/v1/games/${encodeURIComponent(runId)}/stream?${params.toString()}`;
}
