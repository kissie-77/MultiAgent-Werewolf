import React from "react";
import { BeliefSnapshot } from "../api/insightTypes";
import { Eye } from "lucide-react";
import { matrixScale, formatWolfProb, heatColor } from "../lib/beliefFormat";

interface BeliefMatrixPanelProps {
  beliefs: BeliefSnapshot[];
  players: any[];
  roundLabel: string;
  scope: "public" | "god";
  showIdentities?: boolean;
  currentSpeakerSeat?: number | null;
}

const ROLE_ICONS: Record<string, string> = {
  Seer: "🔮", Witch: "🧪", Hunter: "🎯", Werewolf: "🐺", Villager: "👤"
};

export default function BeliefMatrixPanel({ beliefs, players, roundLabel, scope, showIdentities = false, currentSpeakerSeat = null }: BeliefMatrixPanelProps) {
  // 按座位排序玩家
  const sortedPlayers = [...players].sort((a, b) => a.seat - b.seat);
  
  // 存活的观察者
  const observers = sortedPlayers.filter(p => p.alive);
  
  const getBelief = (observerSeat: number, targetSeat: number) => {
    const obs = beliefs.find(b => b.observer_seat === observerSeat);
    if (!obs) return null;
    return obs.first_order.find(f => f.target_seat === targetSeat) || null;
  };

  const { cell, font } = matrixScale(sortedPlayers.length);
  const rowH = font + 14;

  return (
    <div className="flex flex-col border border-amber-900/30 bg-[#0a0808]/90 rounded-md overflow-hidden text-amber-100 font-sans shadow-[0_4px_20px_rgba(0,0,0,0.6)] text-[10px] relative">
      <div className="absolute inset-0 pointer-events-none opacity-20 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] mix-blend-overlay"></div>
      
      {/* Header */}
      <div className="flex justify-between items-center px-3 py-2 border-b border-amber-900/40 bg-zinc-950/80 relative z-10">
        <div className="flex items-center gap-2 text-amber-500">
          <Eye className="w-3.5 h-3.5" />
          <span className="font-serif font-black tracking-widest text-[#d4af37] drop-shadow-[0_0_8px_rgba(212,175,55,0.4)]">信念矩阵</span>
          <span className="text-amber-500/80 text-[10px] font-sans border-l border-amber-900/50 pl-2">谁认为谁是狼</span>
        </div>
        <div className="font-mono text-amber-500/90 font-bold tracking-widest bg-amber-950/30 px-1.5 py-0.5 rounded border border-amber-900/40">{roundLabel}</div>
      </div>
      
      {/* Matrix */}
      <div className="p-2 overflow-x-auto relative z-10">
        <div style={{ display: 'grid', gridTemplateColumns: `auto repeat(${sortedPlayers.length}, ${cell}px)` }} className="gap-1 justify-items-center">
          {/* Top Header Row (Targets) */}
          <div className="text-amber-400/80 text-right w-full pr-1 flex items-end justify-end uppercase font-serif text-[9px] tracking-widest pb-1 border-b border-amber-900/30 mb-1">目标→</div>
          {sortedPlayers.map(p => (
            <div key={p.seat} className={`flex flex-col items-center pb-1 border-b ${p.seat === currentSpeakerSeat ? 'border-amber-500 text-amber-400' : 'border-amber-900/40 text-amber-500/80'} ${!p.alive ? 'opacity-40 grayscale' : ''} mb-1 w-full`}>
              <div className="font-serif font-bold text-[11px]">P{p.seat}</div>
              {showIdentities && (
                <div className="text-[10px] mt-0.5">{scope === 'god' ? ROLE_ICONS[p.role] || '👤' : (!p.alive || p.seat === 1 ? (ROLE_ICONS[p.role] || '👤') : '❓')}</div>
              )}
            </div>
          ))}

          {/* Rows (Observers) */}
          {observers.map(obs => {
            const isSpeaker = obs.seat === currentSpeakerSeat;
            return (
              <React.Fragment key={obs.id}>
                {/* Row Header */}
                <div className={`text-right w-full pr-2 flex items-center justify-end gap-1 ${isSpeaker ? 'text-amber-400 font-bold font-serif' : 'text-amber-500/80 font-serif'}`}>
                  <span>P{obs.seat}</span>
                  {showIdentities && <span className="text-[10px] opacity-80">{ROLE_ICONS[obs.role] || '👤'}</span>}
                </div>
                
                {/* Cells */}
                {sortedPlayers.map(target => {
                  if (!target.alive) {
                    return (
                      <div key={target.seat} className="w-full flex items-center justify-center p-0.5 opacity-30 relative group">
                        <div className="w-full flex items-center justify-center text-amber-700/80 bg-black/40 border border-amber-900/20 rounded-sm font-serif" style={{ height: rowH }}>†</div>
                      </div>
                    );
                  }

                  const cellData = getBelief(obs.seat, target.seat);
                  const isSelf = obs.seat === target.seat;

                  let content = "·";
                  let bgCol = "transparent";
                  let borderCol = "transparent";
                  let cls = "text-amber-900/40";
                  let tooltip = "";

                  if (isSelf) {
                    content = "✕";
                    bgCol = "rgba(0,0,0, 0.4)";
                    borderCol = "rgba(120, 53, 15, 0.3)";
                    cls = "text-amber-600/60";
                    tooltip = `P${obs.seat} 是本人`;
                  } else if (cellData) {
                    const p = cellData.wolf_probability;
                    bgCol = heatColor(p);
                    borderCol = "rgba(245, 158, 11, 0.2)";
                    // 颜色 + 百分比数字
                    content = formatWolfProb(p);
                    cls = "text-white font-mono drop-shadow-[0_1px_1.5px_rgba(0,0,0,0.9)] font-bold";
                    tooltip = `P${obs.seat} 认为 P${target.seat} 狼概率 ${(p*100).toFixed(0)}% · ${cellData.reason || cellData.note || ''}`;
                  }

                  return (
                    <div 
                      key={target.seat} 
                      className={`w-full flex items-center justify-center rounded-sm cursor-crosshair group relative transition-all ${isSpeaker || target.seat === currentSpeakerSeat ? 'ring-1 ring-amber-500/40 z-10' : ''}`}
                      style={{ height: rowH, backgroundColor: bgCol, borderColor: borderCol, borderWidth: borderCol !== 'transparent' ? '1px' : '0' }}
                    >
                      <span className={cls} style={{ fontSize: font }}>{content}</span>
                      
                      {/* Tooltip */}
                      <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity z-50 bg-[#0f0a05] border border-amber-900/60 text-amber-100 px-2 flex flex-col py-1.5 rounded-sm bottom-full mb-1 whitespace-nowrap shadow-[0_5px_15px_rgba(0,0,0,0.8)] pointer-events-none w-max max-w-[200px] whitespace-normal break-words font-sans before:content-[''] before:absolute before:top-full before:left-1/2 before:-translate-x-1/2 before:border-4 before:border-transparent before:border-t-amber-900/60">
                        <span className="font-serif text-amber-500/80 text-[8px] mb-0.5 border-b border-amber-900/40 pb-0.5">读心结界</span>
                        {tooltip}
                      </div>
                    </div>
                  );
                })}
              </React.Fragment>
            );
          })}
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex justify-between items-center px-3 py-1.5 bg-black/60 text-[8px] text-amber-400/80 font-serif relative z-10 border-t border-amber-900/30">
        <div>"✕" = 本人 | "†" = 亡者</div>
        <div className="flex items-center gap-1 font-mono uppercase tracking-widest text-[7px] text-amber-500/90">
          Min <div className="w-1.5 h-1.5 rounded-[1px] bg-[rgb(15,50,100)] border border-amber-900/30"></div>
          <div className="w-1.5 h-1.5 rounded-[1px] bg-[rgb(217,119,6)] border border-amber-900/30"></div>
          <div className="w-1.5 h-1.5 rounded-[1px] bg-[rgb(153,27,27)] border border-amber-900/30"></div> Max
        </div>
      </div>
    </div>
  );
}
