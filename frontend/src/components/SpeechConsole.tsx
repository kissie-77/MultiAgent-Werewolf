import React, { useEffect, useRef } from "react";
import { MessageSquare, Scroll } from "lucide-react";
import { useGameStore } from "../store";

interface SpeechConsoleProps {
  isExpanded?: boolean;
  onToggle?: () => void;
}

export default function SpeechConsole({ isExpanded = true, onToggle }: SpeechConsoleProps) {
  const gameState = useGameStore((state) => state.state);
  const speechLogs = gameState?.speechLogs || [];
  const currentSpeakerId = gameState?.currentSpeakerId;
  const currentNarration = gameState?.narration || "幽暗城堡的丧钟敲响，所有人各就各位...";

  const listEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs to bottom when something changes
  useEffect(() => {
    if (isExpanded) {
      listEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [speechLogs, currentSpeakerId, isExpanded]);

  return (
    <div className="flex flex-col flex-grow bg-transparent overflow-hidden relative z-10">
      {/* Wooden Comic Banner Header */}
      <div className="flex items-center justify-between bg-transparent px-4 py-1.5 border-b border-zinc-900/50 select-none">
        <div className="flex items-center gap-2">
          {/* Gothic Scroll Icon */}
          <Scroll className="w-4 h-4 text-red-600 animate-pulse" />
          <span className="font-sans font-black text-xs tracking-widest text-zinc-100 uppercase ink-shadow">
            ⚖ 审判会议发言及演说记录 ⚖
          </span>
        </div>
        
        {/* Toggle & count indicators */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-[9px] text-[#e0e0e0]/70">
            <MessageSquare className="w-3.5 h-3.5 text-yellow-500" />
            <span>共 {speechLogs.length} 条记录</span>
          </div>
          {onToggle && (
            <button
              onClick={onToggle}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-black/30 hover:bg-black/60 border border-zinc-800 rounded text-[10px] text-zinc-300 font-mono font-black uppercase tracking-widest cursor-pointer transition-all active:scale-95"
              title={isExpanded ? "收起演说记录" : "展开演说记录"}
            >
              {isExpanded ? (
                <>
                  <span>收起</span>
                  <span className="text-red-500 font-bold">▼</span>
                </>
              ) : (
                <>
                  <span>展开</span>
                  <span className="text-emerald-500 font-bold">▲</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Narrative & Guidance Banner */}
      <div className="bg-transparent p-3 border-b border-zinc-900/30 flex gap-3 items-start">
        <div className="w-8 h-8 rounded shrink-0 bg-red-950/40 border border-red-800/60 flex items-center justify-center text-red-500 font-serif font-black text-sm animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.4)]">
          ☠
        </div>
        <div className="flex-grow min-w-0">
          <span className="font-mono text-[9px] uppercase text-red-500 tracking-widest font-black block mb-0.5">
            [ 审判官裁决引导布告 ]
          </span>
          <p className="font-sans text-xs text-[#e0e0e0] leading-relaxed font-black font-serif">
            {currentNarration}
          </p>
        </div>
      </div>

      {/* List of Speeches & Debates - Wrapped styled as dynamic high-focus Parchment elements */}
      <div className="flex-grow overflow-y-auto px-4 py-4 space-y-4 font-sans select-text bg-transparent">
        {speechLogs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-600 gap-2 py-8">
            <span className="font-serif text-4xl text-zinc-800 animate-pulse">☠</span>
            <span className="font-mono text-xs tracking-widest text-zinc-700 uppercase font-black">风平浪静 虚无之地</span>
          </div>
        ) : (
          speechLogs.map((log, index) => {
            const isNarrator = log.role === "NARRATOR";
            const isSelf = log.playerId === 1;
            const isActingSpeaker = currentSpeakerId === log.playerId;

            if (isNarrator) {
              return (
                <div key={index} className="flex justify-center my-3">
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
              <div
                key={index}
                className={`flex gap-3 max-w-[90%] ${isSelf ? "ml-auto flex-row-reverse" : "mr-auto"}`}
              >
                {/* Avatar Badge */}
                <div className={`w-10 h-10 rounded shrink-0 flex flex-col items-center justify-center font-mono font-black text-xs shadow-md ${
                  isSelf 
                    ? "bg-amber-100 border-2 border-amber-900 text-amber-950"
                    : isActingSpeaker
                      ? "bg-yellow-400 border-2 border-black text-black ring-2 ring-yellow-400/80 animate-pulse"
                      : "bg-black border-2 border-zinc-800 text-zinc-400"
                }`}>
                  <span className="text-[10px] opacity-60">P</span>
                  <span className="text-sm -mt-1">{log.playerId}</span>
                </div>

                {/* Speech Bubble - parchment paper style with safe horizontal padding of px-7 */}
                <div className={`relative px-7 py-4 rounded-lg border-2 shadow-2xl parchment text-zinc-920 font-serif max-w-lg ${
                  isSelf
                    ? "rounded-tr-none shadow-[4px_4px_0px_0px_rgba(255,255,255,0.1)]"
                    : isActingSpeaker
                      ? "rounded-tl-none ring-2 ring-yellow-400/50"
                      : "rounded-tl-none opacity-90"
                }`}>
                  {/* Speaker name */}
                  <div className="flex items-center justify-between gap-6 border-b border-black/20 pb-1.5 mb-2 font-mono text-[9px] font-black uppercase tracking-wider text-black">
                    <span className={`${isSelf ? "text-red-800 font-black" : "text-blue-900 font-black"}`}>
                      {log.playerName} {isSelf && "(你)"}
                    </span>
                    <span className="text-zinc-700 tracking-widest">
                      DAY {log.day} 论辩
                    </span>
                  </div>

                  {/* Speech words */}
                  <p className="text-[12.5px] leading-relaxed font-sans font-extrabold whitespace-pre-wrap text-[#1a1a1a]">
                    {log.content}
                  </p>

                  {/* Decorative tiny ink spot */}
                  <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-black rounded-full opacity-10 pointer-events-none" />
                </div>
              </div>
            );
          })
        )}
        {/* Dynamic bottom cushion so elements do not overlap or cover scrollable speech lines */}
        {currentSpeakerId !== null && currentSpeakerId !== 1 && (
          <div className="h-10 shrink-0" />
        )}
        <div ref={listEndRef} />
      </div>

      {/* Floating typing state if active AI is thinking */}
      {currentSpeakerId !== null && currentSpeakerId !== 1 && (
        <div className="absolute bottom-2 left-4 bg-black border-2 border-yellow-500/80 px-4 py-1.5 rounded shadow-lg animate-pulse flex items-center gap-2 z-20">
          <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce delay-75" />
          <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce delay-150" />
          <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-bounce delay-200" />
          <span className="font-mono text-[9px] text-yellow-400 font-black uppercase tracking-wider">
            玩家 {currentSpeakerId} 号 撰写逻辑论稿中...
          </span>
        </div>
      )}
    </div>
  );
}
