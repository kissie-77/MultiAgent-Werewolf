import React, { useEffect, useState } from "react";
import { Sun, Moon, Clock, Flame, LogOut, Home } from "lucide-react";
import { useGameStore } from "../store";

export default function TopHeader({
  onExit,
  isLiveRun = false,
}: {
  onExit?: () => void | Promise<void>;
  isLiveRun?: boolean;
}) {
  const gameState = useGameStore((state) => state.state);
  const phase = gameState?.phase;
  const dayNumber = gameState?.dayNumber || 1;
  const isAutoPlaying = useGameStore((state) => state.isAutoPlaying);
  const toggleAutoPlay = useGameStore((state) => state.toggleAutoPlay);
  const simulateNextAI = useGameStore((state) => state.simulateNextAI);
  const exitGame = useGameStore((state) => state.exitGame);

  const [localSecondsLeft, setLocalSecondsLeft] = useState<number>(30);
  const [confirmExit, setConfirmExit] = useState(false);

  useEffect(() => {
    if (confirmExit) {
      const timer = setTimeout(() => {
        setConfirmExit(false);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [confirmExit]);

  // Sync / Reset local countdown timer when phase changes
  useEffect(() => {
    setLocalSecondsLeft(30);
  }, [phase, dayNumber]);

  // Live countdown ticker
  useEffect(() => {
    const interval = setInterval(() => {
      setLocalSecondsLeft((prev) => {
        if (prev <= 1) {
          return 30; // Auto recycle countdown
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Safe check when countdown timer reaches zero
  useEffect(() => {
    if (isLiveRun) return;
    if (localSecondsLeft === 1) {
      if (isAutoPlaying && phase === "DAY_DEBATE" && gameState?.currentSpeakerId !== 1) {
        simulateNextAI();
      }
    }
  }, [localSecondsLeft, isAutoPlaying, phase, simulateNextAI, gameState?.currentSpeakerId, isLiveRun]);

  useEffect(() => {
    if (isLiveRun) return;
    let timeout: NodeJS.Timeout;
    if (isAutoPlaying && phase === "DAY_DEBATE" && gameState?.currentSpeakerId !== 1) {
      timeout = setTimeout(() => {
        simulateNextAI();
      }, 5500);
    }
    return () => clearTimeout(timeout);
  }, [isAutoPlaying, phase, simulateNextAI, gameState?.currentSpeakerId, isLiveRun]);

  if (!gameState) return null;

  const isNight = phase?.startsWith("NIGHT");

  return (
    <div className="w-full h-12 bg-black/45 backdrop-blur-md border-b border-zinc-900/60 px-6 py-1.5 shrink-0 flex items-center justify-between relative z-10 shadow-md">
      
      {/* Dynamic logo / indicator */}
      <div className="flex items-center gap-1">
        <div className="w-1.5 h-5 bg-red-650" />
        <div className="w-0.5 h-5 bg-red-800" />
        <div className="hidden sm:flex flex-col ml-2 font-sans text-[9px] text-zinc-100 uppercase tracking-widest font-black leading-tight">
          <span>狼人杀神圣审判厅</span>
          <span className="text-[8px] text-zinc-500">{gameState.winner ? "已结案" : "对决轮转中"}</span>
        </div>
      </div>

      {/* Centerpiece: Holy Trial Phase Badge (石碑法阵框式) */}
      <div className="flex items-center gap-4 bg-black/55 backdrop-blur-xs border border-zinc-800/50 px-6 py-1 rounded relative shadow-[0_2px_4px_rgba(0,0,0,0.4)]"
           style={{ clipPath: "polygon(0 0, 100% 0, 95% 100%, 5% 100%)" }}>
        
        {/* Phase Iconography */}
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
 
          {/* Phase Title text */}
          <div className="flex flex-col">
            <span className="font-serif font-black text-xs text-zinc-100 tracking-wider">
              {isNight ? `夜暮降临 • 第 ${dayNumber} 晚` : `曙光黎明 • 第 ${dayNumber} 日`}
            </span>
            <span className="font-mono text-[9px] text-[#eab308]/90 tracking-widest font-black uppercase">
              {phase === "ROLE_CHOICE" && "宿命契约抉择"}
              {phase === "NIGHT_WOLF" && "狼人潜行屠杀"}
              {phase === "NIGHT_SEER" && "神灵探秘查验"}
              {phase === "NIGHT_WITCH" && "女巫配药抉择"}
              {phase === "DAY_ANNOUNCEMENT" && "审判布告死讯"}
              {phase === "DAY_DEBATE" && "圆形议事辩驳中"}
              {phase === "DAY_VOTE" && "封印公投决战"}
              {phase === "GAME_OVER" && "审判宿命终结"}
            </span>
          </div>
        </div>

        {/* Separator */}
        <div className="w-1 h-6 bg-zinc-800" />

        {/* Live Timer Countdown Deck */}
        <div className="flex items-center gap-2">
          <Clock className={`w-4 h-4 ${localSecondsLeft <= 10 ? "text-red-600 animate-bounce" : "text-zinc-500"}`} />
          <span className={`font-mono font-black text-sm tracking-wider ${
            localSecondsLeft <= 10 ? "text-red-600 animate-pulse" : "text-zinc-100"
          }`}>
            00:{localSecondsLeft < 10 ? `0${localSecondsLeft}` : localSecondsLeft}
          </span>
        </div>

        {/* Separator */}
        <div className="w-px h-6 bg-zinc-700 mx-1" />

        {!isLiveRun && (
        <button
          onClick={toggleAutoPlay}
          className={`h-6 px-2 rounded border text-[10px] font-sans font-bold tracking-wider cursor-pointer flex items-center justify-center transition-all duration-200 ${
            isAutoPlaying 
              ? "border-amber-500/50 bg-amber-500/20 text-amber-500 hover:bg-amber-500/30 shadow-[0_0_8px_rgba(245,158,11,0.2)]" 
              : "border-emerald-500/50 bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.2)]"
          }`}
          title={isAutoPlaying ? "暂停游戏自动播放" : "继续游戏自动播放"}
        >
          {isAutoPlaying ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          )}
        </button>
        )}
      </div>

      {/* Right-side Quick statistics */}
      <div className="flex items-center gap-4">
        {/* Go back  */}
        <button
          onClick={() => window.history.back()}
          className="h-7 px-2.5 rounded border border-zinc-800 transition-all duration-200 bg-zinc-950/30 hover:bg-zinc-900/50 text-zinc-400 text-[10px] font-mono hover:text-zinc-200 uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          返回上一级
        </button>

        {/* Go to rules / Dashboard */}
        <button
          onClick={() => window.location.href = '/home'}
          className="h-7 px-2.5 rounded border border-indigo-900/60 transition-all duration-200 bg-indigo-950/30 hover:bg-indigo-900/40 text-blue-200 text-[10px] font-mono hover:text-white uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          <Home className="w-3.5 h-3.5" />
          回到主界面
        </button>

        {/* Count survivors vs count deceased */}
        <div className="text-right font-mono text-[9.5px] leading-tight hidden xs:block">
          <div className="text-yellow-500 font-extrabold uppercase tracking-wider">
            存活已降临: {gameState.players.filter(p => p.isAlive).length}名
          </div>
          <div className="text-red-600 font-black uppercase tracking-wider mt-0.5">
            已被撕咬放逐: {gameState.players.filter(p => !p.isAlive).length}名
          </div>
        </div>

        {/* Exit Game Button (推出游戏/退出) */}
        <button
          onClick={() => {
            if (confirmExit) {
              if (onExit) {
                void onExit();
              } else {
                void exitGame();
              }
              setConfirmExit(false);
            } else {
              setConfirmExit(true);
            }
          }}
          className={`h-7 px-2.5 rounded border text-[10px] font-sans font-bold tracking-wider cursor-pointer flex items-center gap-1 transition-all duration-200 ${
            confirmExit
              ? "border-red-500 bg-red-600 text-white shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse"
              : "border-red-900/60 bg-red-950/30 hover:bg-red-900/40 text-red-100 hover:text-white"
          }`}
          title="退出当前游戏"
          id="exit-game-header-btn"
        >
          <LogOut className="w-3 h-3 animate-spin" style={{ animationDuration: confirmExit ? '1.5s' : '0s' }} />
          <span>{confirmExit ? "二次点击确认退出" : "退出游戏"}</span>
        </button>

        {/* Decorative Holy Fire */}
        <div className="w-7 h-7 rounded border border-zinc-800/40 bg-black/40 flex items-center justify-center shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
          <Flame className="w-3.5 h-3.5 text-red-500 animate-pulse" />
        </div>
      </div>
    </div>
  );
}
