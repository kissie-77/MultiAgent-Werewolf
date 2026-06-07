import React from "react";
import { motion, AnimatePresence } from "motion/react";
import { BrainCircuit, SlidersHorizontal } from "lucide-react";
import type { AvailableModelOption } from "../api/types";

/** 左栏：智脑深度 + 警长竞选 */
export function SetupBrainSheriffPanel({
  enableDeepGame,
  onToggleDeepGame,
  hasSheriff,
  onSheriffChange,
}: {
  enableDeepGame: boolean;
  onToggleDeepGame: () => void;
  hasSheriff: boolean;
  onSheriffChange: (v: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <span className="font-serif text-[10px] text-amber-600/70 tracking-[0.25em] uppercase">
        进阶仪轨 · Advanced
      </span>

      <div className="flex flex-col gap-3">
        <div className="rounded-lg border border-slate-800/90 bg-black/25 p-3 flex flex-col gap-2">
          <button
            type="button"
            onClick={onToggleDeepGame}
            className={`w-full flex items-center justify-between rounded border transition-all duration-200 p-2.5 ${
              enableDeepGame
                ? "bg-violet-900/20 border-violet-500/40 text-violet-300"
                : "bg-black/30 border-slate-800 text-slate-500 hover:border-slate-700"
            }`}
          >
            <span className="flex items-center gap-2 text-[10px] font-sans font-bold tracking-widest text-left">
              <BrainCircuit className="w-4 h-4 shrink-0" />
              智脑深度
            </span>
            <span className={`text-[10px] font-mono tabular-nums shrink-0 ${enableDeepGame ? "text-violet-400" : "text-zinc-600"}`}>
              {enableDeepGame ? "ON" : "OFF"}
            </span>
          </button>
          <AnimatePresence initial={false}>
            {enableDeepGame && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden text-[9px] text-zinc-500 font-sans leading-relaxed px-0.5"
              >
                观战时可查看 AI 信念矩阵与投票意向；关闭后不再采集相关数据。
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        <div className="rounded-lg border border-slate-800/90 bg-black/25 p-3 flex flex-col gap-2">
          <span className="text-[10px] text-amber-500/70 font-serif tracking-widest">警长竞选</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onSheriffChange(true)}
              className={`flex-1 py-2 rounded border text-[10px] font-sans font-bold tracking-widest transition-all ${
                hasSheriff
                  ? "bg-amber-500/15 border-amber-500/50 text-amber-400"
                  : "bg-black/30 border-slate-800 text-slate-500 hover:border-slate-700"
              }`}
            >
              开启警徽流
            </button>
            <button
              type="button"
              onClick={() => onSheriffChange(false)}
              className={`flex-1 py-2 rounded border text-[10px] font-sans font-bold tracking-widest transition-all ${
                !hasSheriff
                  ? "bg-indigo-500/15 border-indigo-500/50 text-indigo-400"
                  : "bg-black/30 border-slate-800 text-slate-500 hover:border-slate-700"
              }`}
            >
              无警徽局
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** 右栏：身份卡下方 — 各席位 AI 模型编排 */
export function SetupModelPanel({
  customizeModels,
  onToggleCustomizeModels,
  modelsLoading,
  availableModels,
  seatProviders,
  onSeatProviderChange,
  effectivePlayerCount,
  humanSeat,
  gameMode,
  defaultProviderId,
}: {
  customizeModels: boolean;
  onToggleCustomizeModels: () => void;
  modelsLoading: boolean;
  availableModels: AvailableModelOption[];
  seatProviders: string[];
  onSeatProviderChange: (index: number, providerId: string) => void;
  effectivePlayerCount: number;
  humanSeat: number;
  gameMode: "llmOnly" | "humanVsAI";
  defaultProviderId: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800/90 bg-black/25 p-3 flex flex-col gap-2">
      <button
        type="button"
        onClick={onToggleCustomizeModels}
        className={`w-full flex items-center justify-between rounded border transition-all duration-200 p-2.5 ${
          customizeModels
            ? "bg-cyan-900/20 border-cyan-500/40 text-cyan-300"
            : "bg-black/30 border-slate-800 text-slate-500 hover:border-slate-700"
        }`}
      >
        <span className="flex items-center gap-2 text-[10px] font-sans font-bold tracking-widest text-left">
          <SlidersHorizontal className="w-4 h-4 shrink-0" />
          模型编排
        </span>
        <span className={`text-[10px] font-mono tabular-nums shrink-0 ${customizeModels ? "text-cyan-400" : "text-zinc-600"}`}>
          {customizeModels ? "ON" : "OFF"}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {!customizeModels ? (
          <motion.p
            key="models-off-hint"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden text-[9px] text-zinc-500 font-sans px-0.5"
          >
            默认全部使用豆包（需在设置中配置 ARK_API_KEY / ARK_EP）。
          </motion.p>
        ) : (
          <motion.div
            key="models-on-panel"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="flex flex-col gap-2 max-h-44 overflow-y-auto custom-scrollbar pt-1">
              {modelsLoading ? (
                <span className="text-[10px] text-zinc-500 font-sans">加载可用模型…</span>
              ) : availableModels.length === 0 ? (
                <span className="text-[10px] text-amber-600/80 font-sans">
                  尚未检测到已配置的供应商，请先点击右上角设置写入 .env。
                </span>
              ) : (
                Array.from({ length: effectivePlayerCount }, (_, index) => {
                  const seat = index + 1;
                  if (gameMode === "humanVsAI" && seat === humanSeat) return null;
                  return (
                    <div key={seat} className="flex items-center gap-2">
                      <span className="text-[10px] text-zinc-500 font-sans w-8 shrink-0">{seat} 号</span>
                      <select
                        value={seatProviders[index] ?? defaultProviderId}
                        onChange={(e) => onSeatProviderChange(index, e.target.value)}
                        className="flex-1 min-w-0 bg-black/60 border border-slate-700 text-amber-100 text-[10px] font-sans px-2 py-1.5 rounded outline-none focus:border-amber-500/50"
                      >
                        {availableModels.map((m) => (
                          <option key={m.provider_id} value={m.provider_id}>
                            {m.display_name} ({m.provider_label})
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
