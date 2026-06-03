import React from "react";
import { Trophy, Skull, Shield, RefreshCw } from "lucide-react";
import { motion } from "motion/react";

export default function GameOverPanel({ winner, onExit }: { winner: string; onExit: () => void }) {
  const isGoodWin = !winner.includes("狼") && winner !== "werewolf";
  const label = isGoodWin ? "好人阵营胜利" : "狼人阵营胜利";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="absolute inset-0 z-50 overflow-y-auto bg-black/90 backdrop-blur-md flex flex-col justify-between p-6 md:p-8 text-zinc-100 font-sans pointer-events-auto"
    >
      {/* Decorative Woodcut borders */}
      <div className="absolute inset-4 pointer-events-none border border-yellow-600/35 rounded z-0" />
      <div className="absolute inset-5 pointer-events-none border border-zinc-800/80 rounded z-0" />

      {/* Top Banner Area */}
      <div className="text-center mt-4 mb-4 relative z-10 shrink-0">
        <motion.div
          initial={{ y: -20 }}
          animate={{ y: 0 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="inline-block"
        >
          {isGoodWin ? (
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-16 h-16 rounded-full bg-yellow-500/10 border-2 border-yellow-500 flex items-center justify-center text-yellow-500 animate-pulse shadow-[0_0_20px_rgba(234,179,8,0.3)]">
                <Shield className="w-10 h-10" />
              </div>
              <h1 className="text-3xl font-black tracking-[0.2em] font-sans text-yellow-500 mt-2 uppercase">
                朝 晖 复 苏 ∙ 好 人 捷 报
              </h1>
              <p className="font-mono text-[10px] text-zinc-400 uppercase tracking-widest mt-0.5">
                Dawn Awakens: The Sacred Alliance of Light Prevails
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-16 h-16 rounded-full bg-red-950/15 border-2 border-red-500 flex items-center justify-center text-red-500 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.3)]">
                <Skull className="w-10 h-10" />
              </div>
              <h1 className="text-3xl font-black tracking-[0.2em] font-sans text-red-500 mt-2 uppercase">
                暗 夜 魔 啸 ∙ 狼 人 暴 虐
              </h1>
              <p className="font-mono text-[10px] text-zinc-400 uppercase tracking-widest mt-0.5">
                Moonless Eclipse: The Lycan Bloodline Conquers All
              </p>
            </div>
          )}
        </motion.div>
      </div>

      {/* Result Details */}
      <div className="flex-grow flex flex-col items-center justify-center gap-6 relative z-10">
        <div className="bg-zinc-950/80 border border-zinc-800 rounded-lg p-8 flex flex-col items-center gap-4 shadow-2xl max-w-md w-full">
          <Trophy className={`w-12 h-12 ${isGoodWin ? "text-yellow-500" : "text-red-500"}`} />
          <h2 className={`text-2xl font-black font-sans uppercase tracking-widest ${isGoodWin ? "text-yellow-400" : "text-red-400"}`}>
            {label}
          </h2>
          <p className="font-mono text-[11px] text-zinc-400 text-center leading-relaxed">
            阵营：<span className={`font-bold ${isGoodWin ? "text-yellow-500" : "text-red-500"}`}>{winner}</span>
          </p>
          <div className="w-16 h-0.5 bg-zinc-800 my-2" />
          <p className="font-serif text-xs text-zinc-300 text-center italic leading-relaxed">
            {isGoodWin
              ? "正义终将战胜黑暗，AI 们以逻辑与推理驱逐了潜伏的恶狼。"
              : "黑暗在圆桌间蔓延，AI 狼人以迷惑与欺骗征服了整座圆桌。"}
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="text-center relative z-10 py-4 shrink-0 flex flex-col items-center gap-3">
        <h4 className="text-[9.5px] text-zinc-500 font-mono tracking-widest uppercase">
          — 宿命交织的下一场轮回 已经在大门外敲响 —
        </h4>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={onExit}
            className="group relative px-8 py-3 font-sans font-black text-[11px] uppercase tracking-wider text-black bg-yellow-500 hover:bg-yellow-400 border border-yellow-700/60 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5 group-hover:rotate-180 transition-transform duration-500" />
            返回配置 · 再开一局
          </button>
        </div>
      </div>
    </motion.div>
  );
}
