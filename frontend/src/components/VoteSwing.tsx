import React, { useState } from "react";
import { VoteSwingSpeech, TimelineEvent } from "../api/types";
import { TrendingUp, Users, MessageSquareQuote } from "lucide-react";
import { motion } from "motion/react";

export default function VoteSwing({ swings, timeline }: { swings: VoteSwingSpeech[], timeline: TimelineEvent[] }) {
  const [selectedSwing, setSelectedSwing] = useState<string | null>(swings[0]?.id || null);

  const activeSwing = swings.find(s => s.id === selectedSwing);

  return (
    <div className="border border-zinc-900 bg-zinc-950/40 rounded p-6">
      <div className="flex flex-col sm:flex-row justify-between sm:items-end mb-8 border-b border-zinc-900 pb-4">
        <div>
          <h3 className="font-serif text-lg text-amber-500 tracking-widest flex items-center gap-2">
            投票摇摆 ∙ 谁的发言带动了改票
          </h3>
          <p className="text-xs font-mono text-zinc-500 mt-1 uppercase">
            Vote Swing Network
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Ranking */}
        <div className="lg:col-span-1 border-r border-zinc-900 pr-6 space-y-4">
          <h4 className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-4 flex items-center justify-between">
            <span>影响力榜</span>
            <span>改票量</span>
          </h4>
          <div className="space-y-3">
             {swings.sort((a,b) => b.influence_score - a.influence_score).map(s => (
               <div 
                 key={s.id} 
                 onClick={() => setSelectedSwing(s.id)}
                 className={`group cursor-pointer rounded p-2 transition-all ${selectedSwing === s.id ? 'bg-amber-500/10 border border-amber-500/30' : 'hover:bg-zinc-900/50 border border-transparent'}`}
               >
                 <div className="flex items-center justify-between mb-1.5">
                   <div className="flex items-center gap-1.5">
                     <span className="font-mono text-sm font-bold text-zinc-300">{s.speaker_id}</span>
                     <span className="text-[10px] text-zinc-500">{s.speaker_role}</span>
                   </div>
                   <div className="font-mono text-xs text-amber-500 font-bold flex items-center gap-1">
                     {s.influence_score} <span className="text-zinc-600 font-normal">({s.swing_count}改)</span>
                   </div>
                 </div>
                 {/* Bar */}
                 <div className="w-full h-1 bg-zinc-900 rounded-full overflow-hidden">
                   <motion.div 
                     initial={{ width: 0 }}
                     animate={{ width: `${Math.min(s.influence_score * 3, 100)}%` }}
                     className={`h-full ${selectedSwing === s.id ? 'bg-amber-500' : 'bg-zinc-700 group-hover:bg-zinc-500'}`}
                   />
                 </div>
               </div>
             ))}
          </div>
        </div>

        {/* Right Column: Flow */}
        <div className="lg:col-span-2 flex flex-col min-h-[300px]">
           {activeSwing ? (
             <motion.div 
               key={activeSwing.id}
               initial={{ opacity: 0, x: 10 }}
               animate={{ opacity: 1, x: 0 }}
               className="flex-1 flex flex-col"
             >
                <div className="text-xs font-mono text-zinc-500 mb-6 flex items-center justify-between bg-zinc-950 p-2 rounded border border-zinc-900">
                  <span className="text-amber-500 font-bold">R{activeSwing.round} ∙ {activeSwing.speaker_id} 发言所致改票</span>
                  <span>{activeSwing.swing_count} 票改印</span>
                </div>

                <div className="flex-1 bg-zinc-900/20 border border-zinc-800 border-dashed rounded flex flex-col justify-center items-center p-8 relative">
                  {/* Flow items */}
                  {activeSwing.swings.map((swing, idx) => (
                    <div key={idx} className="flex justify-between items-center w-full max-w-[400px] mb-4">
                      {/* Before */}
                      <div className="w-20 text-center space-y-1">
                        <div className="w-8 h-8 rounded-full bg-zinc-900 border border-zinc-700 mx-auto flex items-center justify-center font-mono text-xs text-zinc-400 font-bold">
                          {swing.voter_id}
                        </div>
                        <div className="text-[10px] font-mono text-zinc-500 uppercase">{swing.from_target || '无'}</div>
                      </div>

                      {/* Line */}
                      <div className="flex-1 relative mx-4">
                         <div className="absolute top-1/2 left-0 w-full h-[1px] bg-gradient-to-r from-zinc-800 to-amber-500/50" />
                         <div className="absolute top-1/2 right-0 w-2 h-2 -translate-y-1/2 translate-x-1 rotate-45 border-t border-r border-amber-500/50" />
                      </div>

                      {/* After */}
                      <div className="w-20 text-center space-y-1">
                        <div className="w-8 h-8 rounded-full bg-amber-500/10 border border-amber-500/50 mx-auto flex items-center justify-center font-mono text-xs text-amber-500 font-bold ring-2 ring-amber-500/20">
                          {swing.to_target}
                        </div>
                        <div className="text-[10px] font-mono text-amber-500/50 uppercase">改投</div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Speech context */}
                <div className="mt-6 bg-[#0a0a0a] border border-zinc-900 rounded p-4 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-amber-500" />
                  <MessageSquareQuote className="w-4 h-4 text-zinc-600 absolute right-4 top-4" />
                  <div className="text-[10px] font-mono text-amber-500 uppercase tracking-widest mb-2 font-bold flex items-center gap-2">
                    {activeSwing.speaker_id} · 原声回笼
                  </div>
                  <p className="text-sm text-zinc-300 font-sans leading-relaxed">
                    "{activeSwing.public_speech}"
                  </p>
                </div>
             </motion.div>
           ) : (
             <div className="flex-1 flex items-center justify-center text-xs font-mono text-zinc-600">
               请在左侧选择以查看票型摇摆网络
             </div>
           )}
        </div>
      </div>
    </div>
  );
}
