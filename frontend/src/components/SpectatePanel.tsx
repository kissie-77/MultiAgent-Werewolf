import { Link } from "react-router-dom";
import { Activity, Loader2, Radio, Square } from "lucide-react";
import GlassPanel from "./ui/GlassPanel";
import { useSpectate } from "../hooks/useSpectate";

const STATUS_LABEL: Record<string, string> = {
  pending: "排队中",
  running: "对局进行中",
  completed: "已结束",
  failed: "失败",
  cancelled: "已取消",
};

interface SpectatePanelProps {
  defaultPlayerCount?: number;
  compact?: boolean;
}

export default function SpectatePanel({ defaultPlayerCount = 6, compact = false }: SpectatePanelProps) {
  const { runId, status, pageData, loading, error, active, startSpectate, stopSpectate } = useSpectate();

  if (!active) {
    return (
      <GlassPanel className={compact ? "mx-auto max-w-md text-center" : "mx-auto max-w-lg text-center"}>
        <div className="mb-3 flex items-center justify-center gap-2 font-mono text-[10px] uppercase tracking-widest text-purple-300">
          <Radio className="h-3.5 w-3.5" />
          API 观战联调
        </div>
        <p className="mb-4 font-mono text-[10px] leading-relaxed text-zinc-500">
          通过 werewolf-api 启动 Demo 局并轮询 <code className="text-zinc-400">/api/v1/games/…/status</code>
        </p>
        <button
          type="button"
          disabled={loading}
          onClick={() => startSpectate(defaultPlayerCount)}
          className="stone-btn flex w-full items-center justify-center gap-2 rounded px-6 py-3 font-serif text-sm font-black uppercase tracking-widest text-zinc-100 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4 text-yellow-500" />}
          启动观战 Demo 局
        </button>
        {error && <p className="mt-3 font-mono text-[10px] text-red-400">{error}</p>}
      </GlassPanel>
    );
  }

  const snapshot = status?.snapshot ?? pageData?.snapshot;
  const events = pageData?.recent_events ?? [];

  return (
    <GlassPanel
      title={`观战 · ${runId}`}
      className={compact ? "mx-auto max-w-md" : "mx-auto max-w-2xl"}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-yellow-400">
          {STATUS_LABEL[status?.status ?? ""] ?? status?.status}
        </span>
        <div className="flex gap-2">
          {status?.has_replay && runId && (
            <Link
              to={`/replay/${runId}`}
              className="rounded border border-zinc-700 px-2 py-1 font-mono text-[9px] uppercase text-zinc-300 hover:border-yellow-500/50"
            >
              复盘
            </Link>
          )}
          <button
            type="button"
            onClick={() => stopSpectate()}
            className="flex items-center gap-1 rounded border border-zinc-700 px-2 py-1 font-mono text-[9px] uppercase text-zinc-400 hover:text-red-300"
          >
            <Square className="h-3 w-3" />
            停止
          </button>
        </div>
      </div>

      {snapshot && (
        <div className="mb-4 grid grid-cols-2 gap-2 font-mono text-[10px] text-zinc-400 sm:grid-cols-4">
          <div>阶段：{snapshot.phase ?? "—"}</div>
          <div>回合：{snapshot.round_number}</div>
          <div>存活：{snapshot.alive_count}</div>
          <div>事件：{snapshot.event_count}</div>
        </div>
      )}

      {status?.result_text && (
        <p className="mb-3 rounded border border-zinc-800 bg-zinc-950/60 p-2 font-mono text-[10px] text-zinc-300">
          {status.result_text}
        </p>
      )}

      {error && <p className="mb-3 font-mono text-[10px] text-red-400">{error}</p>}

      <div className="max-h-48 overflow-y-auto rounded border border-zinc-900/80 bg-black/40 p-2">
        {events.length === 0 ? (
          <p className="py-4 text-center font-mono text-[10px] text-zinc-600">等待事件流…</p>
        ) : (
          <ul className="space-y-1.5">
            {events.slice(-30).map((ev) => (
              <li key={ev.index} className="font-mono text-[9px] leading-relaxed text-zinc-400">
                <span className="text-zinc-600">
                  R{ev.round_number}·{ev.phase}
                </span>{" "}
                <span className="text-purple-400/80">[{ev.event_type}]</span> {ev.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </GlassPanel>
  );
}
