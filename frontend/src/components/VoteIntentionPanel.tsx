import React from "react";
import { VoteIntentionSnapshot } from "../api/insightTypes";
import { motion, AnimatePresence } from "motion/react";
import { Users } from "lucide-react";

interface VoteIntentionPanelProps {
  snapshot: VoteIntentionSnapshot;
  players: any[];
  showIdentities?: boolean;
}

const ROLE_ICONS: Record<string, string> = {
  Seer: "🔮", Witch: "🧪", Hunter: "🎯", Werewolf: "🐺", Villager: "👤"
};

export default React.memo(function VoteIntentionPanel({ snapshot, players, showIdentities = false }: VoteIntentionPanelProps) {
  const getPlayerInfo = (id: string | null) => {
    if (!id) return null;
    const p = players.find(p => p.id === id);
    if (!p) return null;
    return { ...p, icon: ROLE_ICONS[p.role] || "👤" };
  };

  const getSeatInfo = (seat: number) => {
    if (seat === 0) return { icon: "", text: "观望" };
    const p = players.find(p => p.seat === seat);
    return p ? { icon: ROLE_ICONS[p.role], text: `P${seat}` } : { icon: "", text: "未知" };
  };

  // 将 before/after 对象映射为数组
  const voterIds = Object.keys(snapshot.after);

  // 用于统计
  const tally: Record<number, number> = {};
  voterIds.forEach(vid => {
    const seat = snapshot.after[vid].seat;
    tally[seat] = (tally[seat] || 0) + 1;
  });
  
  // 排序统计条目
  const tallyEntries = Object.entries(tally).sort((a, b) => b[1] - a[1]);

  return (
    <div className="flex flex-col border border-amber-900/30 bg-[#0a0808]/90 rounded-md overflow-hidden text-amber-100 font-sans shadow-[0_4px_20px_rgba(0,0,0,0.6)] text-[10px] mt-4 relative">
      <div className="absolute inset-0 pointer-events-none opacity-20 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] mix-blend-overlay"></div>

      {/* Header */}
      <div className="flex justify-between items-center px-3 py-2 border-b border-amber-900/40 bg-zinc-950/80 relative z-10">
        <div className="flex items-center gap-2 text-amber-500">
          <Users className="w-3.5 h-3.5 text-amber-600" />
          <span className="font-serif font-black tracking-widest text-[#d4af37] drop-shadow-[0_0_8px_rgba(212,175,55,0.4)]">投票意向</span>
        </div>
        {snapshot.swing_count > 0 && (
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            key={snapshot.speaker_id}
            className="font-serif text-[9px] text-[#0a0808] bg-amber-500/90 px-2 py-0.5 rounded-sm font-bold tracking-widest leading-none drop-shadow-md border border-amber-400"
          >
            ▲ {snapshot.swing_count} 人改票
          </motion.div>
        )}
      </div>

      {/* Rows */}
      <div className="p-2 space-y-1 relative z-10">
        <AnimatePresence mode="popLayout">
          {voterIds.map(vid => {
            const before = snapshot.before[vid];
            const after = snapshot.after[vid];
            if (!after) return null;

            const voter = getPlayerInfo(after.player_id);
            if (!voter) return null;

            const isChanged = before && before.seat !== after.seat;

            const targetBefore = before ? getSeatInfo(before.seat) : null;
            const targetAfter = getSeatInfo(after.seat);

            return (
              <motion.div 
                key={vid}
                layout
                initial={{ backgroundColor: "rgba(0,0,0,0)" }}
                animate={{ backgroundColor: isChanged ? ["rgba(245,158,11,0.15)", "rgba(0,0,0,0)"] : "rgba(0,0,0,0)" }}
                transition={{ duration: 1.5 }}
                className={`flex flex-col py-1.5 px-1.5 border-b border-amber-900/10 last:border-b-0 ${isChanged ? 'border-l-[3px] border-l-amber-500 pl-1.5 -ml-[3px] bg-amber-900/10' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-serif text-amber-500/90 font-bold text-[11px] w-6 text-center">
                      P{voter.seat}{showIdentities && <span className="text-[10px] opacity-80 inline-block ml-0.5">{voter.icon}</span>}
                    </span>
                    <div className="flex items-center gap-1.5 font-sans text-[10px]">
                      {isChanged ? (
                        <>
                          <span className="text-amber-600/80 line-through opacity-80">{targetBefore?.text}</span>
                          <span className="text-amber-500/80 text-[8px] font-black">──▶</span>
                          <span className="text-amber-400 font-bold tracking-wider">{targetAfter.text}</span>
                          <span className="text-amber-500/80 font-serif ml-1 text-[8px] italic">(改)</span>
                        </>
                      ) : (
                        <>
                          <span className="text-amber-200/90 font-medium tracking-wider">{targetAfter.text}</span>
                          <span className="text-amber-600/80 font-serif ml-1 text-[8px] italic">(持)</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                {after.reason && (
                  <div className="text-[9px] text-amber-300/70 italic pl-8 pr-1 mt-1 max-w-full truncate border-l border-amber-900/30 ml-1.5" title={after.reason}>
                    "{after.reason}"
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <div className="border-t border-amber-900/30 bg-black/40 p-3 pb-2 relative z-10">
         <div className="text-amber-400/90 mb-2 font-serif text-[9px] tracking-widest uppercase mb-1.5 border-b border-amber-900/20 pb-1">票型预测</div>
         <div className="flex items-center gap-3 font-mono flex-wrap">
           {tallyEntries.map(([seatStr, count], idx) => {
             const seat = parseInt(seatStr);
             const info = getSeatInfo(seat);
             return (
               <React.Fragment key={seat}>
                 {idx > 0 && <span className="text-amber-900/30">|</span>}
                 <span className="flex items-center gap-1.5 bg-amber-950/20 px-1.5 py-0.5 rounded border border-amber-900/20">
                   <span className="font-serif text-amber-300/90 text-[10px]">{seat === 0 ? "观望" : `P${seat}`}</span>
                   <div className="flex gap-0.5">
                     {Array.from({ length: count }).map((_, i) => (
                       <div key={i} className="w-1.5 h-3 bg-amber-500/80 rounded-sm"></div>
                     ))}
                   </div>
                   <span className="text-amber-400 font-bold ml-0.5">{count}</span>
                 </span>
               </React.Fragment>
             );
           })}
         </div>
      </div>

      <div className="px-3 py-2 bg-[#050403] text-amber-400/80 border-t border-amber-900/40 relative z-10 font-serif text-[9px] italic flex items-center justify-between">
        <span>因发言更易: P{getPlayerInfo(snapshot.speaker_id)?.seat}</span>
        <span className="opacity-80">影响力 {snapshot.influence_score}</span>
      </div>
    </div>
  );
})
