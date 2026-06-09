import React, { useState, useMemo, useEffect } from "react";
import { BeliefAnchor } from "../api/types";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default React.memo(function BeliefHeatmap({
  anchors,
  selectedDay,
}: {
  anchors: BeliefAnchor[];
  /** Optional day filter: only show anchors for this round. */
  selectedDay?: number;
}) {
  const [cursor, setCursor] = useState(0);
  const [matrixMode, setMatrixMode] = useState<"B1" | "B2">("B1");
  const [hoveredCell, setHoveredCell] = useState<{
    obs: string;
    target: string;
    reason?: string;
    note?: string;
    prob: number;
  } | null>(null);

  // Filter anchors by selected day (round number)
  const dayAnchors = useMemo(() => {
    if (!anchors?.length) return [];
    if (selectedDay == null) return anchors;
    return anchors.filter((a) => a.round === selectedDay);
  }, [anchors, selectedDay]);

  // Reset cursor when day changes or filtered list changes
  useEffect(() => {
    setCursor(0);
  }, [dayAnchors.length, selectedDay]);

  const activeAnchor = dayAnchors[cursor];

  // 动态推导玩家列表
  const seats = useMemo(() => {
    if (!dayAnchors.length) return ["P1", "P2", "P3", "P4", "P5", "P6"];
    const seatNumbers = new Set<number>();
    for (const anchor of dayAnchors) {
      for (const obs of anchor.observers ?? []) {
        const n = parseInt(String(obs.observer_id).replace(/\D/g, ""), 10);
        if (Number.isFinite(n) && n > 0) seatNumbers.add(n);
        for (const t of obs.targets ?? []) {
          const tn = parseInt(String(t.target_seat).replace(/\D/g, ""), 10);
          if (Number.isFinite(tn) && tn > 0) seatNumbers.add(tn);
        }
        for (const t of obs.secondOrderTargets ?? []) {
          const tn = parseInt(String(t.target_seat).replace(/\D/g, ""), 10);
          if (Number.isFinite(tn) && tn > 0) seatNumbers.add(tn);
        }
      }
    }
    const sorted = Array.from(seatNumbers).sort((a, b) => a - b);
    return sorted.length > 0
      ? sorted.map((n) => `P${n}`)
      : ["P1", "P2", "P3", "P4", "P5", "P6"];
  }, [dayAnchors]);

  const getCellColor = (prob: number | undefined, note?: string) => {
    if (note === "已死") return "bg-zinc-900 border-zinc-800 text-zinc-600";
    if (prob === undefined) return "bg-zinc-950 border-zinc-900";
    if (prob === 0)
      return matrixMode === "B1"
        ? "bg-blue-500/20 border-blue-500/30 text-blue-400"
        : "bg-violet-500/20 border-violet-500/30 text-violet-400";
    if (prob < 0.5) return "bg-zinc-800 border-zinc-700 text-zinc-300";
    if (prob === 1.0)
      return matrixMode === "B1"
        ? "bg-red-600 border-red-500 text-white font-bold"
        : "bg-fuchsia-600 border-fuchsia-500 text-white font-bold";
    if (prob > 0.5)
      return matrixMode === "B1"
        ? "bg-orange-600 border-orange-500 text-orange-200"
        : "bg-pink-600 border-pink-500 text-pink-200";
    return "bg-zinc-800 border-zinc-700 text-zinc-300";
  };

  const getCellLabel = (prob: number | undefined, note?: string) => {
    if (note === "本人" || note === "已死") return "·";
    if (prob === undefined) return "·";
    return prob.toFixed(2).replace(/^0+/, "");
  };

  const getTargets = (
    obs: typeof dayAnchors[number]["observers"][number],
  ) => {
    return matrixMode === "B1"
      ? obs.targets ?? []
      : obs.secondOrderTargets ?? [];
  };

  const modeName = matrixMode === "B1" ? "一阶信念" : "二阶信念";
  const modeSubtitle =
    matrixMode === "B1" ? "谁认为谁是狼" : "谁怀疑谁怀疑我";

  if (!dayAnchors.length) {
    return (
      <div className="border border-zinc-900 bg-zinc-950/40 rounded p-6">
        <h3 className="font-serif text-lg text-amber-500 tracking-widest flex items-center gap-2">
          信念矩阵
        </h3>
        <p className="text-xs text-zinc-500 mt-4">
          {selectedDay != null
            ? `D${selectedDay} 阶段暂无信念快照数据。`
            : "暂无信念快照数据，或对局尚未产生信念记录。"}
        </p>
      </div>
    );
  }

  if (!activeAnchor) return null;

  return (
    <div className="border border-zinc-900 bg-zinc-950/40 rounded p-6">
      <div className="flex flex-col sm:flex-row justify-between sm:items-end mb-8 border-b border-zinc-900 pb-4">
        <div>
          <h3 className="font-serif text-lg text-amber-500 tracking-widest flex items-center gap-2">
            信念矩阵 ∙ 《{modeSubtitle}》
            {selectedDay != null && (
              <span className="text-xs font-mono text-zinc-500 ml-2">
                D{selectedDay}
              </span>
            )}
          </h3>
          <p className="text-xs font-mono text-zinc-500 mt-1 uppercase">
            Belief Evolution Matrix — {modeName}
          </p>
        </div>

        <div className="flex items-center gap-4 mt-4 sm:mt-0">
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

          <div className="flex items-center gap-3 bg-zinc-900 rounded p-1">
            <button
              disabled={cursor === 0}
              onClick={() => setCursor((c) => c - 1)}
              className="p-1 text-zinc-500 hover:text-zinc-300 disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono text-amber-400 min-w-[70px] text-center">
              {activeAnchor?.label}
            </span>
            <button
              disabled={cursor === dayAnchors.length - 1}
              onClick={() => setCursor((c) => c + 1)}
              className="p-1 text-zinc-500 hover:text-zinc-300 disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="flex overflow-x-auto pb-4 items-center justify-center">
        <div className="min-w-max">
          <div className="flex items-center h-8 mb-2">
            <div className="w-20 shrink-0 font-sans text-xs text-zinc-600 text-right pr-4">
              {matrixMode === "B1" ? "观察者 ↓" : "被观察者 ↓"}
            </div>
            <div className="flex gap-1">
              {seats.map((s) => (
                <div
                  key={s}
                  className="w-12 text-center font-mono text-xs text-zinc-500"
                >
                  {s}
                </div>
              ))}
            </div>
            <div className="text-xs font-sans text-zinc-600 pl-4 w-24">
              {matrixMode === "B1" ? "←目标" : "←怀疑者"}
            </div>
          </div>

          <div className="space-y-1">
            {seats.map((obs) => {
              const observerData =
                activeAnchor?.observers?.find(
                  (o) => o.observer_id === obs,
                );

              if (matrixMode === "B2" && observerData) {
                const targets = getTargets(observerData);
                if (targets.length === 0) return null;
              } else if (!observerData) {
                return null;
              }

              const targets = getTargets(observerData!);

              return (
                <div key={obs} className="flex items-center gap-1">
                  <div className="w-20 shrink-0 text-right pr-4 font-mono text-xs text-zinc-400 font-bold border-r border-zinc-800 bg-zinc-900/50 py-1.5 rounded-l">
                    {obs}
                  </div>

                  {seats.map((target) => {
                    const tData = targets.find(
                      (t) => t.target_seat === target,
                    );
                    const isHovered =
                      hoveredCell?.obs === obs &&
                      hoveredCell?.target === target;

                    return (
                      <div
                        key={target}
                        onMouseEnter={() =>
                          setHoveredCell({
                            obs,
                            target,
                            reason: tData?.reason,
                            note: tData?.note,
                            prob: tData?.wolf_probability ?? 0,
                          })
                        }
                        onMouseLeave={() => setHoveredCell(null)}
                        className={`w-12 h-8 flex items-center justify-center text-xs font-mono border rounded-sm cursor-default transition-all ${getCellColor(tData?.wolf_probability, tData?.note)} ${isHovered ? "ring-2 ring-amber-500 scale-110 z-10" : ""}`}
                      >
                        {getCellLabel(tData?.wolf_probability, tData?.note)}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-8 h-12 flex items-center justify-center border border-zinc-900 bg-zinc-950 rounded p-2 text-xs font-mono">
        {hoveredCell ? (
          <div className="flex items-center gap-2">
            <span className="text-amber-500">
              [{hoveredCell.obs} → {hoveredCell.target}]
            </span>
            <span className="text-zinc-500">
              {matrixMode === "B1" ? "狼概率" : "疑我度"}:{" "}
              <strong className="text-zinc-300">
                {(hoveredCell.prob * 100).toFixed(0)}%
              </strong>
            </span>
            {(hoveredCell.reason || hoveredCell.note) && (
              <>
                <span className="text-zinc-700">|</span>
                <span className="text-zinc-400">
                  {hoveredCell.reason || hoveredCell.note}
                </span>
              </>
            )}
          </div>
        ) : (
          <span className="text-zinc-600">
            悬停单元格查看认知详情与推理缘由...
          </span>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between text-[10px] font-mono text-zinc-500">
        <div className="flex items-center gap-3">
          <span>图例: </span>
          {matrixMode === "B1" ? (
            <>
              <span className="text-blue-400">好人 (0%)</span>
              <span className="text-zinc-500 mx-1">·</span>
              <span className="text-orange-400">疑似 (50%+)</span>
              <span className="text-zinc-500 mx-1">·</span>
              <span className="text-red-500">铁狼 (100%)</span>
            </>
          ) : (
            <>
              <span className="text-violet-400">无怀疑 (0%)</span>
              <span className="text-zinc-500 mx-1">·</span>
              <span className="text-pink-400">有疑 (50%+)</span>
              <span className="text-zinc-500 mx-1">·</span>
              <span className="text-fuchsia-500">强疑 (100%)</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
});
