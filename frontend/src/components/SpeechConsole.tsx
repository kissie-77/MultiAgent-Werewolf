import React, { useEffect, useRef } from "react";
import { MessageSquare, Scroll, Brain } from "lucide-react";
import { useGameStore } from "../store";
import { RenderLog } from "../types";

interface SpeechConsoleProps {
  isExpanded?: boolean;
  onToggle?: () => void;
}

function EventRow({ log }: { log: RenderLog }) {
  // 非发言事件：居中系统行
  if (log.kind !== "speech") {
    const tone =
      log.kind === "death" ? "text-red-400 border-red-900/60"
      : log.kind === "vote" ? "text-yellow-400 border-yellow-900/50"
      : log.kind === "skill" ? "text-fuchsia-300 border-fuchsia-900/50"
      : log.kind === "phase" ? "text-zinc-300 border-zinc-700"
      : "text-zinc-400 border-zinc-800";
    return (
      <div className="flex justify-center my-2">
        <div className={`bg-black/70 border px-3 py-1 rounded text-center max-w-[85%] ${tone}`}>
          <p className="font-mono text-[11px] font-bold">{log.text}</p>
        </div>
      </div>
    );
  }
  // 发言气泡 + 内心 OS
  return (
    <div className="flex gap-3 max-w-[90%] mr-auto">
      <div className="w-10 h-10 rounded shrink-0 flex flex-col items-center justify-center font-mono font-black text-xs shadow-md bg-black border-2 border-zinc-800 text-zinc-300">
        <span className="text-[10px] opacity-60">P</span>
        <span className="text-sm -mt-1">{log.speakerSeat ?? "?"}</span>
      </div>
      <div className="relative px-7 py-4 rounded-lg border-2 shadow-2xl parchment font-serif max-w-lg rounded-tl-none">
        <div className="flex items-center justify-between gap-6 border-b border-black/20 pb-1.5 mb-2 font-mono text-[9px] font-black uppercase tracking-wider text-black">
          <span className="text-blue-900">{log.speakerName || `玩家 ${log.speakerSeat}`}</span>
          <span className="text-zinc-700 tracking-widest">DAY {log.day}</span>
        </div>
        <p className="text-[12.5px] leading-relaxed font-sans font-extrabold whitespace-pre-wrap text-[#1a1a1a]">
          {log.text}
        </p>
        {log.privateThought && (
          <div className="mt-2 pt-2 border-t border-dashed border-black/30 bg-fuchsia-950/10 -mx-3 px-3 rounded">
            <span className="flex items-center gap-1 font-mono text-[8px] uppercase tracking-widest text-fuchsia-800 font-black mb-0.5">
              <Brain className="w-3 h-3" /> 内心 OS（上帝视角）
            </span>
            <p className="text-[11px] italic text-fuchsia-950/90 whitespace-pre-wrap">{log.privateThought}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SpeechConsole({ isExpanded = true, onToggle }: SpeechConsoleProps) {
  const logs = useGameStore((s) => s.logs);
  const snapshot = useGameStore((s) => s.snapshot);
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isExpanded) listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, isExpanded]);

  const narration = snapshot?.phase_label || "幽暗城堡的丧钟敲响，AI 们各就各位...";

  return (
    <div className="flex flex-col flex-grow bg-transparent overflow-hidden relative z-10">
      <div className="flex items-center justify-between bg-transparent px-4 py-1.5 border-b border-zinc-900/50 select-none">
        <div className="flex items-center gap-2">
          <Scroll className="w-4 h-4 text-red-600 animate-pulse" />
          <span className="font-sans font-black text-xs tracking-widest text-zinc-100 uppercase ink-shadow">⚖ AI 审判会议实录 ⚖</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-[9px] text-[#e0e0e0]/70">
            <MessageSquare className="w-3.5 h-3.5 text-yellow-500" />
            <span>共 {logs.length} 条</span>
          </div>
          {onToggle && (
            <button onClick={onToggle} className="flex items-center gap-1.5 px-2.5 py-1 bg-black/30 hover:bg-black/60 border border-zinc-800 rounded text-[10px] text-zinc-300 font-mono font-black uppercase tracking-widest cursor-pointer">
              {isExpanded ? "收起 ▼" : "展开 ▲"}
            </button>
          )}
        </div>
      </div>

      <div className="bg-transparent p-3 border-b border-zinc-900/30 flex gap-3 items-start">
        <div className="w-8 h-8 rounded shrink-0 bg-red-950/40 border border-red-800/60 flex items-center justify-center text-red-500 font-serif font-black text-sm animate-pulse">☠</div>
        <p className="font-sans text-xs text-[#e0e0e0] leading-relaxed font-black font-serif">{narration}</p>
      </div>

      <div className="flex-grow overflow-y-auto px-4 py-4 space-y-3 font-sans select-text bg-transparent">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-600 gap-2 py-8">
            <span className="font-serif text-4xl text-zinc-800 animate-pulse">☠</span>
            <span className="font-mono text-xs tracking-widest text-zinc-700 uppercase font-black">等待 AI 入场…</span>
          </div>
        ) : (
          logs.map((log) => <EventRow key={log.seq} log={log} />)
        )}
        <div ref={listEndRef} />
      </div>
    </div>
  );
}
