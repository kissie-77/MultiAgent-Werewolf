import React, { useEffect, useState } from "react";
import { Sun, Moon, Clock, Flame, LogOut, Home } from "lucide-react";
import { useGameStore } from "../store";

export default React.memo(function TopHeader({
  onExit,
  isLiveRun = false,
}: {
  onExit?: () => void | Promise<void>;
  isLiveRun?: boolean;
}) {
  const gameState = useGameStore((state) => state.state);
  const phase = gameState?.phase;
  const dayNumber = gameState?.dayNumber || 1;
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

  useEffect(() => {
    setLocalSecondsLeft(30);
  }, [phase, dayNumber]);

  useEffect(() => {
    const interval = setInterval(() => {
      setLocalSecondsLeft((prev) => (prev <= 1 ? 30 : prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!gameState) return null;

  const isNight = phase?.startsWith("NIGHT");

  return (
    <div className="w-full h-12 bg-black/45 backdrop-blur-md border-b border-zinc-900/60 px-6 py-1.5 shrink-0 flex items-center justify-between relative z-10 shadow-md">
      <div className="flex items-center gap-1">
        <div className="w-1.5 h-5 bg-red-650" />
        <div className="w-0.5 h-5 bg-red-800" />
        <div className="hidden sm:flex flex-col ml-2 font-sans text-[9px] text-zinc-100 uppercase tracking-widest font-black leading-tight">
          <span>狼人杀神圣审判厅</span>
          <span className="text-[8px] text-zinc-500">{gameState.winner ? "已结案" : isLiveRun ? "实时对局" : "对决轮转中"}</span>
        </div>
      </div>

      <div
        className="flex items-center gap-4 bg-black/55 backdrop-blur-xs border border-zinc-800/50 px-6 py-1 rounded relative shadow-[0_2px_4px_rgba(0,0,0,0.4)]"
        style={{ clipPath: "polygon(0 0, 100% 0, 95% 100%, 5% 100%)" }}
      >
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

        <div className="w-1 h-6 bg-zinc-800" />

        <div className="flex items-center gap-2">
          <Clock className={`w-4 h-4 ${localSecondsLeft <= 10 ? "text-red-600 animate-bounce" : "text-zinc-500"}`} />
          <span
            className={`font-mono font-black text-sm tracking-wider ${
              localSecondsLeft <= 10 ? "text-red-600 animate-pulse" : "text-zinc-100"
            }`}
          >
            00:{localSecondsLeft < 10 ? `0${localSecondsLeft}` : localSecondsLeft}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => window.history.back()}
          aria-label="返回上一级"
          className="h-7 px-2.5 rounded border border-zinc-800 transition-all duration-200 bg-zinc-950/30 hover:bg-zinc-900/50 text-zinc-400 text-[10px] font-mono hover:text-zinc-200 uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          返回上一级
        </button>

        <button
          type="button"
          onClick={() => { window.location.href = "/home"; }}
          aria-label="回到主界面"
          className="h-7 px-2.5 rounded border border-indigo-900/60 transition-all duration-200 bg-indigo-950/30 hover:bg-indigo-900/40 text-blue-200 text-[10px] font-mono hover:text-white uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          <Home className="w-3.5 h-3.5" />
          回到主界面
        </button>

        <div className="text-right font-mono text-[9.5px] leading-tight hidden xs:block">
          <div className="text-yellow-500 font-extrabold uppercase tracking-wider">
            存活已降临: {gameState.players.filter((p) => p.isAlive).length}名
          </div>
          <div className="text-red-600 font-black uppercase tracking-wider mt-0.5">
            已被撕咬放逐: {gameState.players.filter((p) => !p.isAlive).length}名
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            if (confirmExit) {
              if (onExit) {
                void onExit();
              } else {
                exitGame();
              }
              setConfirmExit(false);
            } else {
              setConfirmExit(true);
            }
          }}
          aria-label={confirmExit ? "再次点击确认退出游戏" : "退出游戏"}
          className={`h-7 px-2.5 rounded border text-[10px] font-sans font-bold tracking-wider cursor-pointer flex items-center gap-1 transition-all duration-200 ${
            confirmExit
              ? "border-red-500 bg-red-600 text-white shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse"
              : "border-red-900/60 bg-red-950/30 hover:bg-red-900/40 text-red-100 hover:text-white"
          }`}
          id="exit-game-header-btn"
        >
          <LogOut className="w-3 h-3 animate-spin" style={{ animationDuration: confirmExit ? "1.5s" : "0s" }} />
          <span>{confirmExit ? "二次点击确认退出" : "退出游戏"}</span>
        </button>

        <div className="w-7 h-7 rounded border border-zinc-800/40 bg-black/40 flex items-center justify-center shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
          <Flame className="w-3.5 h-3.5 text-red-500 animate-pulse" />
        </div>
      </div>
    </div>
  );
})
