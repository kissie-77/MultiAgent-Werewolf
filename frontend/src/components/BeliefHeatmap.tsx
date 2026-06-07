import React, { useState, useMemo } from "react";
import { BeliefAnchor } from "../api/types";
import { Play, Pause, ChevronLeft, ChevronRight } from "lucide-react";

export default function BeliefHeatmap({ anchors }: { anchors: BeliefAnchor[] }) {
  const [cursor, setCursor] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<{ obs: string, target: string, reason?: string, note?: string, prob: number } | null>(null);

  const activeAnchor = anchors[cursor];

  // 动态推导玩家列表：从所有 anchors 中提取座位号，确保切换 anchor 时座位列表一致
  const seats = useMemo(() => {
    if (!anchors?.length) return ["P1", "P2", "P3", "P4", "P5", "P6"];
    const seatNumbers = new Set<number>();
    for (const anchor of anchors) {
      for (const obs of (anchor.observers ?? [])) {
        const n = parseInt(String(obs.observer_id).replace(/\D/g, ""), 10);
        if (Number.isFinite(n) && n > 0) seatNumbers.add(n);
        for (const t of (obs.targets ?? [])) {
          const tn = parseInt(String(t.target_seat).replace(/\D/g, ""), 10);
          if (Number.isFinite(tn) && tn > 0) seatNumbers.add(tn);
        }
      }
    }
    const sorted = Array.from(seatNumbers).sort((a, b) => a - b);
    return sorted.length > 0 ? sorted.map(n => `P${n}`) : ["P1", "P2", "P3", "P4", "P5", "P6"];
  }, [anchors]);

  // 根据 wolf_probability 决定颜色的辅助函数
  const getCellColor = (prob: number | undefined, note?: string) => {
    if (note === "已死") return "bg-zinc-900 border-zinc-800 text-zinc-600";
    if (prob === undefined) return "bg-zinc-950 border-zinc-900";
    if (prob === 0) return "bg-blue-500/20 border-blue-500/30 text-blue-400";
    if (prob < 0.5) return "bg-zinc-800 border-zinc-700 text-zinc-300";
    if (prob === 1.0) return "bg-red-600 border-red-500 text-white font-bold";
    if (prob > 0.5) return "bg-orange-600 border-orange-500 text-orange-200";
    return "bg-zinc-800 border-zinc-700 text-zinc-300";
  };

  const getCellLabel = (prob: number | undefined, note?: string) => {
    if (note === "本人" || note === "已死") return "·";
    if (prob === undefined) return "·";
    return prob.toFixed(2).replace(/^0+/, "");
  };

  return (
    <div className="border border-zinc-900 bg-zinc-950/40 rounded p-6">
      <div className="flex flex-col sm:flex-row justify-between sm:items-end mb-8 border-b border-zinc-900 pb-4">
        <div>
          <h3 className="font-serif text-lg text-amber-500 tracking-widest flex items-center gap-2">
            信念矩阵 ∙ 「谁认为谁是狼」
          </h3>
          <p className="text-xs font-mono text-zinc-500 mt-1 uppercase">
            Belief Evolution Matrix
          </p>
        </div>

        <div className="flex items-center gap-4 mt-4 sm:mt-0">
          <div className="flex items-center gap-3 bg-zinc-900 rounded p-1">
            <button 
              disabled={cursor === 0}
              onClick={() => setCursor(c => c - 1)}
              className="p-1 text-zinc-500 hover:text-zinc-300 disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono text-amber-400 min-w-[70px] text-center">
              {activeAnchor?.label}
            </span>
            <button 
              disabled={cursor === anchors.length - 1}
              onClick={() => setCursor(c => c + 1)}
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
             <div className="w-20 shrink-0 font-sans text-xs text-zinc-600 text-right pr-4">观察者 ↓</div>
             <div className="flex gap-1">
               {seats.map(s => (
                 <div key={s} className="w-12 text-center font-mono text-xs text-zinc-500">
                   {s}
                 </div>
               ))}
             </div>
             <div className="text-xs font-sans text-zinc-600 pl-4 w-24">←目标</div>
           </div>

           <div className="space-y-1">
             {seats.map(obs => {
               const observerData = activeAnchor?.observers.find(o => o.observer_id === obs);
               if (!observerData) {
                  return null;
               }

               return (
                 <div key={obs} className="flex items-center gap-1">
                   <div className="w-20 shrink-0 text-right pr-4 font-mono text-xs text-zinc-400 font-bold border-r border-zinc-800 bg-zinc-900/50 py-1.5 rounded-l">
                     {obs}
                   </div>
                   
                   {seats.map(target => {
                      const tData = observerData.targets.find(t => t.target_seat === target);
                      const isHovered = hoveredCell?.obs === obs && hoveredCell?.target === target;

                      return (
                        <div 
                          key={target}
                          onMouseEnter={() => setHoveredCell({ obs, target, reason: tData?.reason, note: tData?.note, prob: tData?.wolf_probability ?? 0 })}
                          onMouseLeave={() => setHoveredCell(null)}
                          className={`w-12 h-8 flex items-center justify-center text-xs font-mono border rounded-sm cursor-default transition-all ${getCellColor(tData?.wolf_probability, tData?.note)} ${isHovered ? 'ring-2 ring-amber-500 scale-110 z-10' : ''}`}
                        >
                           {getCellLabel(tData?.wolf_probability, tData?.note)}
                        </div>
                      )
                   })}
                 </div>
               )
             })}
           </div>
        </div>
      </div>

      <div className="mt-8 h-12 flex items-center justify-center border border-zinc-900 bg-zinc-950 rounded p-2 text-xs font-mono">
         {hoveredCell ? (
            <div className="flex items-center gap-2">
               <span className="text-amber-500">[{hoveredCell.obs} 看 {hoveredCell.target}]</span>
               <span className="text-zinc-500">狼概率: <strong className="text-zinc-300">{(hoveredCell.prob * 100).toFixed(0)}%</strong></span>
               {(hoveredCell.reason || hoveredCell.note) && (
                 <>
                   <span className="text-zinc-700">|</span>
                   <span className="text-zinc-400">{hoveredCell.reason || hoveredCell.note}</span>
                 </>
               )}
            </div>
         ) : (
            <span className="text-zinc-600">悬停单元格查看认知详情与推理缘由...</span>
         )}
      </div>

      <div className="mt-4 flex items-center justify-between text-[10px] font-mono text-zinc-500">
        <div>
          <span>图例: </span>
          <span className="text-blue-400 ml-2">好人 (0%)</span> 
          <span className="text-zinc-500 mx-1">·</span> 
          <span className="text-orange-400">疑似 (50%+)</span> 
          <span className="text-zinc-500 mx-1">·</span> 
          <span className="text-red-500">铁狼 (100%)</span>
        </div>
      </div>
    </div>
  );
}
