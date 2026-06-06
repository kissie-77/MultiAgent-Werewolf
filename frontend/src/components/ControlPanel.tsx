import React from "react";
import { useGameStore } from "../store";
import { Play, Pause, SkipForward, Square, Eye, EyeOff, Gauge } from "lucide-react";
import { GamePhase } from "../types";

export default function ControlPanel() {
  const playState = useGameStore((s) => s.playState);
  const speed = useGameStore((s) => s.speed);
  const revealView = useGameStore((s) => s.revealView);
  const gameState = useGameStore((s) => s.gameState);
  const status = useGameStore((s) => s.status);
  const controlGame = useGameStore((s) => s.controlGame);
  const stepGame = useGameStore((s) => s.stepGame);
  const setSpeed = useGameStore((s) => s.setSpeed);
  const setRevealView = useGameStore((s) => s.setRevealView);
  const cancelGame = useGameStore((s) => s.cancelGame);

  const ended =
    gameState?.phase === GamePhase.ended || status === "cancelled" || status === "error";
  const isPlaying = playState === "playing";

  return (
    <div className="bg-transparent border-t border-zinc-900/35 px-6 py-3 flex flex-wrap items-center justify-center gap-4 relative z-10 shrink-0 select-none min-h-[64px]">
      <button onClick={() => controlGame(isPlaying ? "pause" : "resume")} disabled={ended}
        className={`stone-btn px-5 py-2.5 font-sans font-black text-[#f5f5f5] uppercase tracking-widest rounded shadow-lg flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:scale-105 active:translate-y-1"}`}>
        {isPlaying ? <Pause className="w-4 h-4 text-yellow-500" /> : <Play className="w-4 h-4 text-emerald-500" />}
        {isPlaying ? "暂停" : "继续"}
      </button>

      <button onClick={() => stepGame()} disabled={ended}
        className={`px-4 py-2.5 rounded border border-zinc-800 bg-zinc-950/30 text-zinc-200 font-sans font-black text-xs uppercase tracking-widest flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:text-white hover:border-zinc-600"}`}>
        <SkipForward className="w-4 h-4 text-emerald-400" /> 单步
      </button>

      <div className="flex items-center gap-1.5 bg-zinc-950/30 px-3 py-1.5 rounded border border-zinc-900/50">
        <Gauge className="w-3.5 h-3.5 text-zinc-400" />
        {[1, 2, 4].map((s) => (
          <button key={s} onClick={() => setSpeed(s as 1 | 2 | 4)} disabled={ended}
            className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded ${speed === s ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500" : "text-zinc-400 border border-zinc-800 hover:text-zinc-200"}`}>
            {s}x
          </button>
        ))}
      </div>

      <button onClick={() => setRevealView(revealView === "god" ? "suspense" : "god")}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-950/30 text-[11px] font-mono font-bold text-zinc-300 hover:text-white">
        {revealView === "god" ? <Eye className="w-3.5 h-3.5 text-yellow-500" /> : <EyeOff className="w-3.5 h-3.5 text-zinc-400" />}
        {revealView === "god" ? "上帝视角" : "悬念模式"}
      </button>

      <button onClick={cancelGame} disabled={ended}
        className={`px-4 py-2 rounded border-2 border-red-950 bg-red-900 text-red-100 font-sans font-black text-xs uppercase tracking-widest flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:bg-red-700"}`}>
        <Square className="w-3.5 h-3.5" /> 停止
      </button>

      {ended && <span className="font-mono text-[11px] text-zinc-400 uppercase tracking-widest">对局已结束</span>}
    </div>
  );
}
