import React, { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { BeliefAnchor, TimelineEvent } from "../api/types";
import { Eye, EyeOff } from "lucide-react";

// ── Consistent player colors ──
const PLAYER_COLORS = [
  "#f43f5e", "#3b82f6", "#22c55e", "#eab308", "#a855f7",
  "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
  "#d946ef", "#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6",
  "#ef4444",
];

function colorForPlayer(seatLabel: string, index: number): string {
  return PLAYER_COLORS[index % PLAYER_COLORS.length];
}

/** Extract seat label like "P3" from a playerId like "player_3" or "3". */
function seatLabel(playerId: string | number | null | undefined): string {
  const digits = String(playerId ?? "").replace(/\D/g, "");
  const n = parseInt(digits, 10);
  return Number.isFinite(n) && n > 0 ? `P${n}` : String(playerId ?? "");
}

/* ─── Tooltip content ─── */
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 shadow-xl text-xs font-mono">
      <p className="text-amber-400 font-bold mb-1">{label}</p>
      {payload.map((entry: any) => (
        <div key={entry.name} className="flex items-center gap-2 py-0.5">
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-zinc-400">{entry.name}:</span>
          <span className="text-zinc-200 font-bold">
            {(entry.value * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}

/* ─── Main component ─── */
export default React.memo(function BeliefTrendChart({
  anchors,
  timeline = [],
}: {
  anchors: BeliefAnchor[];
  timeline?: TimelineEvent[];
}) {
  const [matrixMode, setMatrixMode] = useState<"B1" | "B2">("B1");
  const [selectedObserver, setSelectedObserver] = useState<string | null>(null);

  // ── Sort anchors chronologically ──
  const sortedAnchors = useMemo(() => {
    const orderMap: Record<string, number> = {
      initial: 0,
      after_speech: 1,
    };
    return [...anchors].sort((a, b) => {
      if (a.round !== b.round) return a.round - b.round;
      const getOrder = (id: string) => {
        for (const [key, val] of Object.entries(orderMap)) {
          if (id.includes(key)) return val;
        }
        return 99;
      };
      return getOrder(a.anchor_id) - getOrder(b.anchor_id);
    });
  }, [anchors]);

  // ── Derive unique observer IDs from all anchors ──
  const observers = useMemo(() => {
    const set = new Set<string>();
    for (const a of anchors) {
      for (const o of a.observers ?? []) {
        set.add(o.observer_id);
      }
    }
    return Array.from(set).sort((a, b) => {
      const na = parseInt(a.replace(/\D/g, ""), 10);
      const nb = parseInt(b.replace(/\D/g, ""), 10);
      return (isNaN(na) ? 0 : na) - (isNaN(nb) ? 0 : nb);
    });
  }, [anchors]);

  React.useEffect(() => {
    if (!selectedObserver && observers.length > 0) {
      setSelectedObserver(observers[0]);
    }
  }, [observers, selectedObserver]);

  // ── Build a lookup: round -> best anchor ──
  const anchorByRound = useMemo(() => {
    const map = new Map<number, BeliefAnchor>();
    for (const anchor of sortedAnchors) {
      // Later anchors in the same round overwrite earlier ones
      // so we always get the most recent snapshot for that round.
      map.set(anchor.round, anchor);
    }
    return map;
  }, [sortedAnchors]);

  // ── Extract speech events from timeline ──
  const speechEvents = useMemo(() => {
    return timeline.filter((ev) => ev.type === "speech");
  }, [timeline]);

  // ── Build chart data: one point per speech event ──
  const chartData = useMemo(() => {
    if (!selectedObserver || speechEvents.length === 0) return [];

    return speechEvents.map((speech) => {
      const round = speech.day;
      const speaker = seatLabel(speech.playerId);
      const anchor = anchorByRound.get(round);

      const point: Record<string, any> = {
        label: `R${round} · ${speaker}`,
        _rawRound: round,
        _index: 0,
      };

      if (anchor) {
        const obs = anchor.observers?.find(
          (o) => o.observer_id === selectedObserver
        );
        if (obs) {
          const targets =
            matrixMode === "B1"
              ? obs.targets ?? []
              : obs.secondOrderTargets ?? [];

          for (const t of targets) {
            const key = t.target_seat;
            point[key] = t.wolf_probability;
            point[`${key}_reason`] = t.reason;
            point[`${key}_note`] = t.note;
          }
        }
      }

      return point;
    });
  }, [speechEvents, selectedObserver, matrixMode, anchorByRound]);

  // ── Unique target players across all data points ──
  const targetSeats = useMemo(() => {
    const set = new Set<string>();
    for (const point of chartData) {
      for (const key of Object.keys(point)) {
        if (/^P\d+$/.test(key)) {
          set.add(key);
        }
      }
    }
    return Array.from(set).sort((a, b) => {
      const na = parseInt(a.replace("P", ""), 10);
      const nb = parseInt(b.replace("P", ""), 10);
      return na - nb;
    });
  }, [chartData]);

  // ── Y-axis ticks ──
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  if (!anchors.length) {
    return (
      <div className="border border-zinc-900 bg-zinc-950/40 rounded p-6">
        <h3 className="font-serif text-lg text-amber-500 tracking-widest">
          信念变化趋势
        </h3>
        <p className="text-xs text-zinc-500 mt-4">暂无信念快照数据。</p>
      </div>
    );
  }

  return (
    <div className="border border-zinc-900 bg-zinc-950/40 rounded p-6">
      {/* ── Header controls ── */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 border-b border-zinc-900 pb-4">
        <h3 className="font-serif text-base font-black tracking-widest text-amber-500 flex items-center gap-2">
          <Eye className="w-4 h-4" />
          信念变化趋势
          <span className="text-xs font-mono text-zinc-500 ml-1">
            — 按发言顺序
          </span>
        </h3>

        <div className="flex items-center gap-3 flex-wrap">
          {/* B1 / B2 toggle */}
          <div className="flex bg-zinc-900 rounded p-0.5">
            <button
              onClick={() => setMatrixMode("B1")}
              className={`px-2.5 py-1 text-[10px] font-mono tracking-wider rounded transition-colors cursor-pointer ${
                matrixMode === "B1"
                  ? "bg-amber-600 text-black font-bold"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              B1 一阶
            </button>
            <button
              onClick={() => setMatrixMode("B2")}
              className={`px-2.5 py-1 text-[10px] font-mono tracking-wider rounded transition-colors cursor-pointer ${
                matrixMode === "B2"
                  ? "bg-violet-600 text-black font-bold"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              B2 二阶
            </button>
          </div>

          {/* Player selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono text-zinc-500 tracking-wider">
              视角:
            </span>
            <select
              value={selectedObserver ?? ""}
              onChange={(e) => setSelectedObserver(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 text-zinc-200 text-[11px] font-mono px-2 py-1 rounded focus:outline-none focus:border-amber-500 cursor-pointer"
            >
              {observers.map((obs) => (
                <option key={obs} value={obs}>
                  {obs}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── Chart area ── */}
      {chartData.length === 0 ? (
        <div className="flex items-center justify-center py-16 text-zinc-600">
          <p className="text-xs font-mono tracking-wider">
            {selectedObserver
              ? `${selectedObserver} 暂无 ${matrixMode === "B1" ? "一阶" : "二阶"} 信念数据`
              : "请选择观察者"}
          </p>
        </div>
      ) : (
        <div className="w-full" style={{ height: Math.max(300, targetSeats.length * 28 + 80) }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 16, left: 8, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis
                dataKey="label"
                tick={{ fill: "#a1a1aa", fontSize: 9, fontFamily: "monospace" }}
                tickLine={{ stroke: "#3f3f46" }}
                axisLine={{ stroke: "#3f3f46" }}
                angle={-35}
                textAnchor="end"
                height={60}
                interval={0}
              />
              <YAxis
                domain={[0, 1]}
                ticks={yTicks}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: "#a1a1aa", fontSize: 10, fontFamily: "monospace" }}
                tickLine={{ stroke: "#3f3f46" }}
                axisLine={{ stroke: "#3f3f46" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: "10px", fontFamily: "monospace", color: "#a1a1aa" }}
              />
              {targetSeats.map((seat, idx) => {
                // Skip self
                if (seat === selectedObserver) return null;
                const color = colorForPlayer(seat, idx);
                return (
                  <Line
                    key={seat}
                    type="stepAfter"
                    dataKey={seat}
                    name={seat}
                    stroke={color}
                    strokeWidth={2}
                    dot={{ r: 3, fill: color, strokeWidth: 1, stroke: "#18181b" }}
                    activeDot={{ r: 5, fill: color, strokeWidth: 2, stroke: "#18181b" }}
                    connectNulls={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Legend ── */}
      <div className="mt-4 flex items-center justify-between text-[10px] font-mono text-zinc-500">
        <div className="flex items-center gap-3 flex-wrap">
          <span>图例: </span>
          {matrixMode === "B1" ? (
            <>
              <span className="text-blue-400">好人 (0%)</span>
              <span className="text-zinc-600">·</span>
              <span className="text-orange-400">疑似 (50%+)</span>
              <span className="text-zinc-600">·</span>
              <span className="text-red-500">铁狼 (100%)</span>
            </>
          ) : (
            <>
              <span className="text-violet-400">无怀疑 (0%)</span>
              <span className="text-zinc-600">·</span>
              <span className="text-pink-400">有疑 (50%+)</span>
              <span className="text-zinc-600">·</span>
              <span className="text-fuchsia-500">强疑 (100%)</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2 text-zinc-600">
          <EyeOff className="w-3 h-3" />
          <span>悬停折线查看具体百分比</span>
        </div>
      </div>
    </div>
  );
});
