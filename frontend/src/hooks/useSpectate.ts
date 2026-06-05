import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelGame,
  fetchGamePage,
  fetchGameStatus,
  startGame,
  type GamePageData,
  type GameStatusResponse,
} from "../api/game";

const POLL_MS = 2000;

export function useSpectate() {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<GameStatusResponse | null>(null);
  const [pageData, setPageData] = useState<GamePageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const refresh = useCallback(async (id: string) => {
    const [nextStatus, nextPage] = await Promise.all([
      fetchGameStatus(id),
      fetchGamePage(id),
    ]);
    setStatus(nextStatus);
    setPageData(nextPage);
    return nextStatus;
  }, []);

  const startSpectate = useCallback(
    async (playerCount = 6) => {
      setLoading(true);
      setError(null);
      stopPolling();
      try {
        const started = await startGame({
          config_id: "demo-6",
          participation: "all_agent",
          rules: "basic",
          player_count: playerCount,
          run_label: "web-spectate",
        });
        setRunId(started.run_id);
        const first = await refresh(started.run_id);
        timerRef.current = setInterval(() => {
          refresh(started.run_id).then((s) => {
            if (s.status === "completed" || s.status === "failed" || s.status === "cancelled") {
              stopPolling();
            }
          }).catch((err: unknown) => {
            setError(err instanceof Error ? err.message : "轮询失败");
            stopPolling();
          });
        }, POLL_MS);
        if (first.status === "completed" || first.status === "failed" || first.status === "cancelled") {
          stopPolling();
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "启动观战失败");
        setRunId(null);
        setStatus(null);
        setPageData(null);
      } finally {
        setLoading(false);
      }
    },
    [refresh, stopPolling],
  );

  const stopSpectate = useCallback(async () => {
    stopPolling();
    if (runId && status?.status === "running") {
      try {
        await cancelGame(runId);
      } catch {
        // ignore cancel errors on teardown
      }
    }
    setRunId(null);
    setStatus(null);
    setPageData(null);
    setError(null);
  }, [runId, status?.status, stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  return {
    runId,
    status,
    pageData,
    loading,
    error,
    active: runId !== null,
    startSpectate,
    stopSpectate,
    refresh: runId ? () => refresh(runId) : undefined,
  };
}
