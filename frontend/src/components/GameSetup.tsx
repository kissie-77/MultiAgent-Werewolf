import React, { useState, useEffect } from "react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { Cpu, ChevronLeft, Flame, Play } from "lucide-react";
import { PROVIDER_PRESETS, getApiKey, setApiKey, providerById } from "../lib/api-keys";
import { SeatConfig } from "../types";

export default function GameSetup() {
  const startGame = useGameStore((state) => state.startGame);
  const status = useGameStore((state) => state.status);

  const [isConfiguring, setIsConfiguring] = useState(false);
  const [playerCount, setPlayerCount] = useState<number>(6);
  const [enableSheriff, setEnableSheriff] = useState(false);
  const [defaultProvider, setDefaultProvider] = useState<string>(PROVIDER_PRESETS[0].id);
  const [defaultModel, setDefaultModel] = useState<string>(PROVIDER_PRESETS[0].models[0]);
  const [seats, setSeats] = useState<SeatConfig[]>([]);
  // 每个 provider 的 key 输入（受控）
  const [keys, setKeys] = useState<Record<string, string>>(() =>
    Object.fromEntries(PROVIDER_PRESETS.map((p) => [p.id, getApiKey(p.id)]))
  );

  // 人数变化时同步座位列表，套用默认 provider/model
  useEffect(() => {
    setSeats((prev) => {
      const next: SeatConfig[] = [];
      for (let i = 0; i < playerCount; i++) {
        next.push(prev[i] || {
          seat: i + 1, name: `Player${i + 1}`,
          provider: defaultProvider, model: defaultModel,
          base_url: providerById(defaultProvider)?.base_url || "",
        });
      }
      return next;
    });
  }, [playerCount, defaultProvider, defaultModel]);

  const updateSeat = (idx: number, patch: Partial<SeatConfig>) =>
    setSeats((s) => s.map((seat, i) => (i === idx ? { ...seat, ...patch } : seat)));

  const saveKey = (provider: string, val: string) => {
    setKeys((k) => ({ ...k, [provider]: val }));
    setApiKey(provider, val);
  };

  const startMatch = async () => {
    await startGame(seats, { enableSheriff });
  };

  const handlePlayerCountChange = (val: number) => {
    setPlayerCount(Math.max(6, Math.min(20, val)));
  };

  return (
    <div className="w-full max-w-4xl px-4 flex flex-col justify-center items-center py-6 select-none relative z-10 bg-transparent">

      <AnimatePresence mode="wait">
        {!isConfiguring ? (
          /* STATE 1: LANDING SCREEN - ONLY THE "START GAME" BUTTON */
          <motion.div
            key="landing"
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -15 }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
            className="w-full max-w-md bg-transparent p-8 relative text-center"
          >
            {/* Gothic Accents */}
            <div className="absolute top-2 left-2 text-[10px] text-zinc-650 font-mono">🕀</div>
            <div className="absolute top-2 right-2 text-[10px] text-zinc-650 font-mono">🕀</div>
            <div className="absolute bottom-2 left-2 text-[10px] text-zinc-650 font-mono">✝</div>
            <div className="absolute bottom-2 right-2 text-[10px] text-zinc-650 font-mono">✝</div>

            <div className="inline-block px-3 py-1 bg-zinc-900/80 border border-zinc-800 text-[9.5px] text-yellow-500 font-mono tracking-[0.25em] uppercase mb-4">
              🔮 诸神交错 · 狼月落尘 🔮
            </div>

            <h1 className="font-serif text-4xl text-[#e5e5e0] tracking-[0.2em] font-black uppercase mb-3 ink-shadow">
              宿命审判
            </h1>

            <p className="text-[11px] font-mono text-zinc-400 tracking-[0.08em] leading-relaxed max-w-xs mx-auto mb-8">
              在大理石圆盘刻纹和微温烛台前，AI 智能体们展开狼人杀对决。
            </p>

            {/* THE ONLY BUTTON */}
            <button
              onClick={() => setIsConfiguring(true)}
              className="stone-btn relative w-full px-8 py-5 font-serif font-black text-[#f5f5f5] text-lg uppercase tracking-[0.25em] transition-all duration-300 rounded shadow-2xl flex items-center justify-center gap-3 cursor-pointer group active:translate-y-1"
              style={{
                clipPath: "polygon(4% 0%, 96% 0%, 100% 18%, 100% 100%, 0% 100%, 0% 18%)",
              }}
            >
              <div className="absolute inset-x-0 top-0 h-1 bg-zinc-500/30" />
              <Flame className="w-5 h-5 text-red-500 group-hover:animate-bounce" />
              <span>开始游戏</span>
              <Flame className="w-5 h-5 text-red-500 group-hover:animate-bounce" />
            </button>

            <div className="font-mono text-[8px] text-zinc-600 tracking-widest mt-6 uppercase">
              — 点击入座 浮雕圆盘将静静旋转 —
            </div>
          </motion.div>
        ) : (
          /* STATE 2: INTERACTIVE GAME CONFIGURATION PAGE */
          <motion.div
            key="config"
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -15 }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
            className="w-full max-w-2xl bg-transparent p-4 md:p-5 relative"
          >
            {/* Corner cracks */}
            <div className="absolute top-2 left-2 text-[10px] text-zinc-650 font-mono">🕀</div>
            <div className="absolute top-2 right-2 text-[10px] text-zinc-650 font-mono">🕀</div>
            <div className="absolute bottom-2 left-2 text-[10px] text-zinc-650 font-mono">✝</div>
            <div className="absolute bottom-2 right-2 text-[10px] text-zinc-650 font-mono">✝</div>

            {/* Go back helper */}
            <button
              onClick={() => setIsConfiguring(false)}
              className="absolute top-3 left-4 bg-zinc-900/50 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white px-2 py-0.5 text-[9px] font-mono tracking-wider uppercase rounded flex items-center gap-1 cursor-pointer transition-colors"
            >
              <ChevronLeft className="w-2.5 h-2.5" /> 返回
            </button>

            {/* Header Block / Board style */}
            <div className="text-center mb-3 border-b border-zinc-900/40 pb-2 relative mt-2">
              <span className="inline-block px-2.5 py-0.5 bg-zinc-900/60 border border-zinc-800 text-[8px] text-yellow-500 font-mono tracking-[0.2em] uppercase mb-1">
                🔮 契 约 编 织 🔮
              </span>
              <h2 className="font-serif text-lg md:text-xl text-[#e5e5e0] tracking-[0.1em] font-black uppercase mb-0.5">
                审 判 席 位 律 令
              </h2>
              <p className="text-[9px] font-mono text-zinc-450 max-w-sm mx-auto leading-normal">
                规划 AI 席位与逐座位模型配置。
              </p>
            </div>

            <div className="space-y-3.5">

              {/* SEC 2: PLAYER COUNT STEPPER SELECTOR (6 - 20) */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest flex items-center gap-2">
                  <span>席 位 议 员 (Player Seats: 6 - 20)</span>
                  <span className="inline-block h-px flex-grow bg-zinc-900/40" />
                </span>

                <div className="flex flex-col md:flex-row items-center gap-3 bg-transparent border border-zinc-900/60 p-2.5 rounded">
                  {/* Stepper Control */}
                  <div className="flex items-center gap-2.5">
                    <button
                      type="button"
                      onClick={() => handlePlayerCountChange(playerCount - 1)}
                      className="w-7 h-7 rounded border border-zinc-900 text-zinc-400 hover:text-white hover:bg-zinc-900 flex items-center justify-center font-bold text-sm select-none transition-colors cursor-pointer"
                    >
                      -
                    </button>

                    <div className="w-12 text-center animate-pulse">
                      <span className="text-xl font-mono font-black text-yellow-500 block leading-none">
                        {playerCount}
                      </span>
                      <span className="text-[7px] text-zinc-500 uppercase tracking-widest block mt-0.5">席位 Seats</span>
                    </div>

                    <button
                      type="button"
                      onClick={() => handlePlayerCountChange(playerCount + 1)}
                      className="w-7 h-7 rounded border border-zinc-900 text-zinc-400 hover:text-white hover:bg-zinc-900 flex items-center justify-center font-bold text-sm select-none transition-colors cursor-pointer"
                    >
                      +
                    </button>
                  </div>

                  {/* Vertical Divider */}
                  <div className="hidden md:block w-px h-7 bg-zinc-900" />

                  {/* Quick Preset Badges */}
                  <div className="flex flex-wrap items-center gap-1.5 flex-grow justify-center md:justify-start">
                    <span className="text-[8px] text-[#ef4444] border border-red-950/40 bg-red-950/10 px-1 py-0.5 rounded font-black uppercase tracking-wider block">
                      常用刻位:
                    </span>
                    {[6, 8, 9, 12, 16].map((num) => (
                      <button
                        key={num}
                        type="button"
                        onClick={() => handlePlayerCountChange(num)}
                        className={`px-2.5 py-1 rounded text-[11px] font-mono font-bold border transition-all duration-200 cursor-pointer ${
                          playerCount === num
                            ? "bg-yellow-500/10 text-yellow-500 border-yellow-500 shadow-sm"
                            : "bg-transparent text-zinc-550 border-zinc-900 hover:text-zinc-300 hover:border-zinc-800"
                        }`}
                      >
                        {num}人席
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* SEC: 默认模型 + 警长流 */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest">Ⅰ. 默认模型 (Default Model)</span>
                <div className="flex flex-wrap items-center gap-2">
                  <select value={defaultProvider}
                    onChange={(e) => { const p = e.target.value; setDefaultProvider(p); setDefaultModel((providerById(p) ?? PROVIDER_PRESETS[0]).models[0]); }}
                    className="bg-black border border-zinc-800 text-zinc-200 px-2 py-1 text-xs rounded">
                    {PROVIDER_PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                  </select>
                  <select value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)}
                    className="bg-black border border-zinc-800 text-zinc-200 px-2 py-1 text-xs rounded">
                    {(providerById(defaultProvider) ?? PROVIDER_PRESETS[0]).models.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                  <label className="flex items-center gap-1.5 text-xs text-zinc-300 font-mono ml-2">
                    <input type="checkbox" checked={enableSheriff} onChange={(e) => setEnableSheriff(e.target.checked)} className="accent-yellow-500" />
                    警长·警徽流
                  </label>
                </div>
              </div>

              {/* SEC: 各 provider 的 API Key */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest">Ⅱ. API Key (存于本地 localStorage)</span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {PROVIDER_PRESETS.map((p) => (
                    <div key={p.id} className="flex items-center gap-2">
                      <span className="text-[10px] text-zinc-400 font-mono w-24 shrink-0">{p.label}</span>
                      <input type="password" value={keys[p.id] || ""} placeholder="sk-..."
                        onChange={(e) => saveKey(p.id, e.target.value)}
                        className="flex-grow bg-zinc-950/40 border border-zinc-800 text-zinc-200 px-2 py-1 text-xs rounded font-mono" />
                    </div>
                  ))}
                </div>
              </div>

              {/* SEC: 逐座位配置 */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest flex items-center gap-2">
                  <Cpu className="w-3 h-3" /> Ⅲ. 逐座位模型 (Per-seat)
                </span>
                <div className="max-h-56 overflow-y-auto flex flex-col gap-1.5 pr-1">
                  {seats.map((seat, idx) => (
                    <div key={seat.seat} className="flex items-center gap-2 bg-zinc-950/30 border border-zinc-900/60 rounded px-2 py-1">
                      <span className="text-yellow-500 font-mono text-[11px] w-8 shrink-0">#{seat.seat}</span>
                      <input value={seat.name} onChange={(e) => updateSeat(idx, { name: e.target.value })}
                        className="w-24 bg-black border border-zinc-800 text-zinc-200 px-1.5 py-0.5 text-[11px] rounded" />
                      <select value={seat.provider}
                        onChange={(e) => { const p = e.target.value; const preset = providerById(p) ?? PROVIDER_PRESETS[0]; updateSeat(idx, { provider: p, model: preset.models[0], base_url: preset.base_url }); }}
                        className="bg-black border border-zinc-800 text-zinc-300 px-1.5 py-0.5 text-[11px] rounded">
                        {PROVIDER_PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                      </select>
                      <select value={seat.model} onChange={(e) => updateSeat(idx, { model: e.target.value })}
                        className="flex-grow bg-black border border-zinc-800 text-zinc-300 px-1.5 py-0.5 text-[11px] rounded">
                        {(providerById(seat.provider) ?? PROVIDER_PRESETS[0]).models.map((m) => <option key={m} value={m}>{m}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Action Button Segment */}
            <div className="mt-4 pt-3 border-t border-zinc-900/40 flex flex-col items-center w-full">
              <button
                onClick={startMatch}
                disabled={status === "running"}
                className="stone-btn relative w-full md:w-2/3 px-5 py-3 font-serif font-black text-[#f5f5f5] text-xs md:text-sm uppercase tracking-[0.2em] transition-all duration-300 rounded shadow-xl flex items-center justify-center gap-2 cursor-pointer active:translate-y-1"
                style={{
                  clipPath: "polygon(4% 0%, 96% 0%, 100% 18%, 100% 100%, 0% 100%, 0% 18%)",
                }}
              >
                <div className="absolute inset-x-0 top-0 h-0.5 bg-zinc-500/30" />
                <Flame className="w-4 h-4 text-red-500 animate-pulse" />
                <Play className="w-4 h-4 text-emerald-400" />
                <span>开启 AI 对决 (Launch LLM Game)</span>
                <Flame className="w-4 h-4 text-red-500 animate-pulse" />
              </button>

              <div className="font-mono text-[7.5px] text-zinc-500/80 tracking-widest mt-1.5 uppercase">
                AI 玩家将自动运行，你可观战并控制播放速度。
              </div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
