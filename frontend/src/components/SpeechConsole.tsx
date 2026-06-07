import React, { useEffect, useRef, useState } from "react";
import { MessageSquare, Scroll, BrainCircuit, ChevronDown, ChevronUp } from "lucide-react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { getRoleImage } from "../utils/roles";
import { THINKING_CONTEXT_LABEL } from "../lib/liveCue";

export default function SpeechConsole({
  highlightSelfSeat = false,
}: {
  /** True on human seat view — show 本人 badge for the seated player only. */
  highlightSelfSeat?: boolean;
}) {
  const gameState = useGameStore((state) => state.state);
  const humanSeat = useGameStore((state) => state.humanSeat);
  const speechLogs = gameState?.speechLogs || [];
  const currentSpeakerId = gameState?.currentSpeakerId;
  const thinkingCue = gameState?.liveCue?.thinking ?? null;
  const currentNarration = gameState?.narration || "幽暗城堡的丧钟敲响，所有人各就各位...";

  const listEndRef = useRef<HTMLDivElement>(null);
  
  // Track which logs have their thinking process expanded
  const [expandedThoughts, setExpandedThoughts] = useState<Record<number, boolean>>({});
  const [showPureTextHistory, setShowPureTextHistory] = useState(false);
  
  const isAutoPlaying = useGameStore(state => state.isAutoPlaying);

  const toggleThought = (index: number) => {
    setExpandedThoughts(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  // Auto-scroll logs to bottom when something changes
  useEffect(() => {
    if (!showPureTextHistory) {
      setTimeout(() => {
        listEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, [speechLogs.length, currentSpeakerId, expandedThoughts, showPureTextHistory]);


  // Map roles to specific border colors and shadows for their dialogue boxes
  const roleStyles: Record<string, string> = {
    "预言家": "border-cyan-600/70 shadow-[4px_4px_0px_0px_rgba(8,145,178,0.25)]",
    "女巫": "border-purple-600/70 shadow-[4px_4px_0px_0px_rgba(147,51,234,0.25)]",
    "猎人": "border-orange-600/70 shadow-[4px_4px_0px_0px_rgba(234,88,12,0.25)]",
    "狼人": "border-red-700/80 shadow-[4px_4px_0px_0px_rgba(185,28,28,0.25)]",
    "村民": "border-zinc-500/70 shadow-[4px_4px_0px_0px_rgba(113,113,122,0.25)]",
  };

  return (
    <div className="flex flex-col flex-grow bg-transparent overflow-hidden relative z-10">
      {/* Merged Thin Header & Narrative Banner */}
      <div className="flex flex-col md:flex-row items-center justify-between bg-[#0a060e] px-4 py-2 border-b border-indigo-500/20 shadow-[0_4px_20px_rgba(30,58,138,0.1)] select-none shrink-0 relative z-10">
        <div className="flex items-center gap-3 overflow-hidden flex-grow md:mr-4 w-full md:w-auto">
          <div className="w-6 h-6 rounded shrink-0 bg-red-950/40 border border-red-800/60 flex items-center justify-center text-red-500 font-serif font-black text-xs shadow-[0_0_10px_rgba(239,68,68,0.4)] animate-pulse">
            ☠
          </div>
          <div className="flex flex-col truncate min-w-0">
             <span className="font-mono text-[8px] uppercase text-red-500 tracking-widest font-black block leading-none mb-0.5 animate-pulse">
              [ 审判官裁决引导布告 ]
             </span>
             <p className="font-sans text-[11px] text-[#e0e0e0] leading-tight font-bold truncate">
               {currentNarration}
             </p>
          </div>
        </div>
        
        {/* Count indicators and Plain Text Toggle */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => setShowPureTextHistory(!showPureTextHistory)}
            className="flex items-center gap-1.5 px-3 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/50 rounded font-mono text-[9px] text-[#e0e0e0] uppercase tracking-widest transition-colors cursor-pointer"
          >
            <MessageSquare className="w-3.5 h-3.5 text-yellow-500" />
            <span>纯文本记录 / {speechLogs.length} 条</span>
          </button>
        </div>
      </div>

      {showPureTextHistory && (
        <div className="absolute inset-0 z-50 bg-black/95 backdrop-blur flex flex-col pt-12 pb-4 overflow-hidden">
          <button 
             className="absolute top-3 right-4 text-xs font-mono text-zinc-400 hover:text-zinc-100 bg-zinc-900 px-3 py-1 rounded border border-zinc-700 transition"
             onClick={() => setShowPureTextHistory(false)}
          >
            [ 关闭纯文本 / CLOSE ]
          </button>
          <div className="flex-grow overflow-y-auto px-6 py-4 space-y-4 text-sm font-sans text-zinc-300 select-text">
            {speechLogs.map((log, index) => (
              <div key={index} className="border-b border-zinc-800 pb-3">
                 <div className="font-mono text-[10px] text-zinc-500 mb-1 flex items-center gap-2 uppercase tracking-wide">
                   {log.role === "NARRATOR" ? (
                     <span className="text-red-500 font-bold">【审判长】</span>
                   ) : (
                     <>
                       <span className="text-yellow-500 font-bold">[{log.role}] {log.playerName} ({log.playerId}号)</span>
                       <span>D-{log.day} / {log.isNight ? "NIGHT" : "DAY"}</span>
                     </>
                   )}
                 </div>
                 <div className="text-[13px] leading-relaxed whitespace-pre-wrap text-zinc-200">
                   {log.content}
                 </div>
              </div>
            ))}
            {speechLogs.length === 0 && <div className="text-zinc-500 text-center text-xs mt-10 italic">暂无发言记录...</div>}
          </div>
        </div>
      )}

      {/* List of Speeches & Debates - With Mask Image Fade to Top */}
      <div 
        className="flex-grow overflow-y-auto px-4 py-6 space-y-5 font-sans select-text bg-transparent pt-[40px]"
        style={{
          maskImage: "linear-gradient(to bottom, transparent 0%, black 15%, black 100%)",
          WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 15%, black 100%)"
        }}
      >
        {speechLogs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-600 gap-2 py-8">
            <span className="font-serif text-4xl text-zinc-800 animate-pulse">☠</span>
            <span className="font-mono text-xs tracking-widest text-zinc-700 uppercase font-black">风平浪静 虚无之地</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {speechLogs.map((log, index) => {
              const isNarrator = log.role === "NARRATOR";
              const isSelf =
                highlightSelfSeat &&
                humanSeat != null &&
                log.playerId === humanSeat;
              const isActingSpeaker = currentSpeakerId === log.playerId;
              const isThoughtExpanded = expandedThoughts[index];
              
              const bubbleRoleStyle = roleStyles[log.role] || "border-black/20 shadow-[4px_4px_0px_0px_rgba(0,0,0,0.1)]";

              if (isNarrator) {
                return (
                  <div key={index} className="flex justify-center my-3 relative z-0">
                    <div className="bg-black text-yellow-500 border-2 border-[#eab308] px-4 py-1.5 rounded shadow-[3px_3px_0_#000] max-w-[85%] text-center">
                      <span className="font-mono text-[8px] text-red-500 font-black tracking-widest uppercase block mb-0.5">
                        — 审判长宣告 天数: {log.day} —
                      </span>
                      <p className="font-serif text-xs text-[#e0e0e0] font-black">
                        {log.content}
                      </p>
                    </div>
                  </div>
                );
              }

              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                  className={`flex gap-3 max-w-[95%] relative z-0 ${isSelf ? "ml-auto flex-row-reverse" : "mr-auto"}`}
                >
                  {/* Distinct Speaker Avatar */}
                  <div className={`w-12 h-12 rounded shrink-0 flex items-center justify-center font-mono font-black text-xs shadow-xl relative overflow-hidden bg-cover bg-center ${
                    isSelf 
                      ? "border-2 border-amber-900 text-amber-950"
                      : isActingSpeaker
                        ? "border-2 border-black text-black ring-4 ring-yellow-400/80 animate-pulse"
                        : "border-2 border-zinc-700 text-zinc-300"
                  }`} style={{ backgroundImage: `url(${getRoleImage(log.role)})` }}>
                    {/* Shadow overlay to make seat number readable */}
                    <div className="absolute inset-0 bg-black/40 pointer-events-none" />
                    
                    <div className="relative z-10 flex flex-col items-center">
                      <span className="text-[8px] opacity-80 mt-1 uppercase text-white drop-shadow-[0_1px_1px_rgba(0,0,0,1)]">席位</span>
                      <span className="text-xl -mt-1 font-serif leading-none text-white drop-shadow-[0_2px_2px_rgba(0,0,0,1)]">{log.playerId}</span>
                    </div>

                    {/* Tiny sub-badge to show current speaker glow */}
                    {isActingSpeaker && <div className="absolute inset-0 border-2 border-white/50 rounded pointer-events-none" />}
                  </div>

                  {/* Speech Bubble - parchment paper style */}
                  <div className={`relative px-6 py-4 border-[3px] parchment font-serif w-full max-w-xl transition-all duration-300 ${bubbleRoleStyle} ${
                    isSelf ? "rounded-tr-none" : "rounded-tl-none"
                  } ${isActingSpeaker && "ring-4 ring-yellow-400/50 scale-[1.01]"}`}>
                    
                    {/* Clear Speaker Header */}
                    <div className="flex items-center justify-between gap-6 pb-2 mb-3 border-b-2 border-black/10 font-mono text-[11px] font-black uppercase tracking-wider text-black">
                      <span className={`${isSelf ? "text-red-800" : "text-blue-900"} flex items-center gap-1`}>
                        <span className="text-xl leading-none">🗣</span> 
                        <span className="underline decoration-2 underline-offset-2">{log.playerName}</span> 
                        {isSelf && <span className="bg-red-800 text-white px-1.5 py-0.5 text-[9px] rounded-full ml-1">本人</span>}
                        <span className="opacity-70 font-normal ml-2">[{log.role}]</span>
                      </span>
                      <span className="text-zinc-600/80 tracking-widest text-[9px] font-bold">
                        D-{log.day} / {log.isNight ? "NIGHT" : "DAY"}
                      </span>
                    </div>

                    {/* AI Reasoning Section (Only render if reasoning exists) */}
                    {log.reasoning && (
                      <div className="mb-3">
                        <button 
                          onClick={() => toggleThought(index)}
                          className={`flex items-center gap-1.5 font-mono text-[10px] uppercase font-bold tracking-wider transition-colors active:scale-95 ${isThoughtExpanded ? "text-indigo-900" : "text-indigo-600 hover:text-indigo-800"}`}
                        >
                          <BrainCircuit className="w-3.5 h-3.5" />
                          <span>{isThoughtExpanded ? "折叠沉思 (Fold Thoughts)" : "窥视内心 (AI Reasoning)"}</span>
                          {isThoughtExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                        
                        <AnimatePresence>
                          {isThoughtExpanded && (
                            <motion.div 
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="mt-2 mb-3 p-3 bg-zinc-900/10 border border-indigo-900/30 rounded font-code text-[11px] leading-relaxed text-slate-800 font-medium opacity-90 italic space-y-1">
                                <div className="font-bold text-indigo-800 border-b border-indigo-900/15 pb-1 mb-1.5">
                                  【 内部演练与战术考量 】
                                </div>
                                <div className="whitespace-pre-wrap">{log.reasoning}</div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}

                    {/* Speech words */}
                    <p className="text-[13.5px] leading-relaxed font-sans font-extrabold whitespace-pre-wrap text-[#111]">
                      {log.content}
                    </p>

                    {/* Decorative tiny ink spot */}
                    <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-black rounded-full opacity-10 pointer-events-none" />
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
        {/* Dynamic bottom cushion so elements do not overlap or cover scrollable speech lines */}
        {thinkingCue && <div className="h-10 shrink-0" />}
        <div ref={listEndRef} />
      </div>

      {/* Live cue: only visible while backend reports actor_thinking */}
      {thinkingCue && (
        <div
          className="absolute bottom-4 left-6 bg-black border-2 border-yellow-500/80 px-4 py-2 rounded shadow-2xl flex items-center gap-2 z-20"
          data-live-cue="thinking"
          data-seat={thinkingCue.seat}
          data-context={thinkingCue.context}
        >
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce" />
            <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce [animation-delay:120ms]" />
            <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce [animation-delay:240ms]" />
          </div>
          <span className="font-mono text-[10px] text-yellow-400 font-black uppercase tracking-wider ml-1">
            {thinkingCue.playerName}（{thinkingCue.seat}号）正在思考 — {THINKING_CONTEXT_LABEL[thinkingCue.context]}
          </span>
        </div>
      )}
    </div>
  );
}
