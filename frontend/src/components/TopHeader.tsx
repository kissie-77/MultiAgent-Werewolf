import React, { useEffect, useState } from "react";
import { Sun, Moon, Flame, LogOut, Activity } from "lucide-react";
import { useGameStore } from "../store";
import { GamePhase, PHASE_LABELS, SUB_PHASE_LABELS } from "../types";
import { isNightPhase } from "../lib/api";

export default function TopHeader() {
  const gameState = useGameStore((s) => s.gameState);
  const exitToSetup = useGameStore((s) => s.exitToSetup);

  const phase = gameState?.phase ?? GamePhase.setup;
  const round = gameState?.round ?? 0;
  const alive = gameState?.alive_count ?? 0;
  const dead = gameState?.dead_count ?? 0;
  const phaseLabel = PHASE_LABELS[phase] ?? "";
  const subPhaseLabel = gameState?.sub_phase ? SUB_PHASE_LABELS[gameState.sub_phase] ?? gameState.sub_phase : null;
  const ended = phase === GamePhase.ended;
  const isNight = isNightPhase(phase);

  const [confirmExit, setConfirmExit] = useState(false);
  useEffect(() => {
    if (confirmExit) {
      const timer = setTimeout(() => setConfirmExit(false), 4000);
      return () => clearTimeout(timer);
    }
  }, [confirmExit]);

  return (
    <div className="w-full bg-black/45 backdrop-blur-md border-b border-zinc-900/60 px-6 py-1.5 shrink-0 flex items-center justify-between relative z-10 shadow-md">

      {/* Dynamic logo / indicator */}
      <div className="flex items-center gap-1">
        <div className="w-1.5 h-5 bg-red-650" />
        <div className="w-0.5 h-5 bg-red-800" />
        <div className="hidden sm:flex flex-col ml-2 font-sans text-[9px] text-zinc-100 uppercase tracking-widest font-black leading-tight">
          <span>狼人杀神圣审判厅</span>
          <span className="text-[8px] text-zinc-500">{ended ? "已结案" : "对决轮转中"}</span>
        </div>
      </div>

      {/* Centerpiece: phase badge driven by GamePhase */}
      <div className="flex items-center gap-4 bg-black/55 backdrop-blur-xs border border-zinc-800/50 px-6 py-1 rounded relative shadow-[0_2px_4px_rgba(0,0,0,0.4)]"
           style={{ clipPath: "polygon(0 0, 100% 0, 95% 100%, 5% 100%)" }}>

        <div className="flex items-center gap-2">
          {isNight ? (
            <div className="w-7 h-7 rounded-full bg-black border-2 border-[#ef4444] flex items-center justify-center text-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]">
              <Moon className="w-4 h-4 fill-red-500 animate-pulse" />
            </div>
          ) : (
            <div className="w-7 h-7 rounded-full bg-black border-2 border-yellow-500 flex items-center justify-center text-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]">
              <Sun className="w-4 h-4 animate-spin-slow" />
            </div>
          )}

          <div className="flex flex-col">
            <span className="font-serif font-black text-xs text-zinc-100 tracking-wider">
              {isNight ? `夜暮降临 • 第 ${round} 晚` : `曙光黎明 • 第 ${round} 日`}
            </span>
            <span className="font-mono text-[9px] text-[#eab308]/90 tracking-widest font-black uppercase">
              {phaseLabel}
            </span>
          </div>
        </div>

        {/* Sub-phase highlight (display hint, not a pause point) */}
        {subPhaseLabel && (
          <>
            <div className="w-1 h-6 bg-zinc-800" />
            <div className="flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-fuchsia-400 animate-pulse" />
              <span className="font-mono font-black text-[11px] tracking-wider text-fuchsia-300">
                {subPhaseLabel}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Right-side stats + exit */}
      <div className="flex items-center gap-4">
        <div className="text-right font-mono text-[9.5px] leading-tight hidden xs:block">
          <div className="text-yellow-500 font-extrabold uppercase tracking-wider">存活: {alive}名</div>
          <div className="text-red-600 font-black uppercase tracking-wider mt-0.5">出局: {dead}名</div>
        </div>

        <button
          onClick={() => {
            if (confirmExit) { exitToSetup(); setConfirmExit(false); }
            else setConfirmExit(true);
          }}
          className={`h-7 px-2.5 rounded border text-[10px] font-sans font-bold tracking-wider cursor-pointer flex items-center gap-1 transition-all duration-200 ${
            confirmExit
              ? "border-red-500 bg-red-600 text-white shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse"
              : "border-red-900/60 bg-red-950/30 hover:bg-red-900/40 text-red-100 hover:text-white"
          }`}
          title="退出当前游戏"
          id="exit-game-header-btn"
        >
          <LogOut className="w-3 h-3" style={{ animationDuration: confirmExit ? "1.5s" : "0s" }} />
          <span>{confirmExit ? "二次点击确认退出" : "退出游戏"}</span>
        </button>

        <div className="w-7 h-7 rounded border border-zinc-800/40 bg-black/40 flex items-center justify-center shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
          <Flame className="w-3.5 h-3.5 text-red-500 animate-pulse" />
        </div>
      </div>
    </div>
  );
}
