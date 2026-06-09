import React from "react";
import { Link } from "react-router-dom";
import { useGameSetup } from "../hooks/useGameSetup";
import BoardSetupPanel from "./BoardSetupPanel";
import { SetupBrainSheriffPanel, SetupModelPanel } from "./SetupAdvancedPanel";
import { motion, AnimatePresence } from "motion/react";
import { Users, Shield, Cpu, Zap, Eye, Skull, Settings, Play } from "lucide-react";
import ApiKeysSettingsModal from "./ApiKeysSettingsModal";
import AudioControls from "./AudioControls";
import { ApiClient } from "../api/client";
import { getTarotImage } from "../utils/roles";

const roleDetails: Record<string, { name: string; desc: string; color: string; icon: React.ReactNode; tag: string }> = {
  预言家: {
    name: "预言家 (Seer)",
    desc: "查验底牌，指引真相。每个黑夜可以查验一名玩家的真实阵营，是指引好人阵营在白昼认清形势的明灯。",
    color: "border-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)] text-amber-500",
    icon: <Eye className="w-5 h-5" />,
    tag: "神职 · 阵营向导"
  },
  女巫: {
    name: "女巫 (Witch)",
    desc: "掌控生死，双药并济。拥有一瓶能使夜间牺牲者复苏的解药，以及一瓶可以毒杀任意玩家的强力毒药。",
    color: "border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.2)] text-purple-400",
    icon: <Shield className="w-5 h-5" />,
    tag: "神职 · 双面利刃"
  },
  猎人: {
    name: "猎人 (Hunter)",
    desc: "终局威慑，退场带人。在被投票流放或狼人袭击出局时（除被女巫毒死外），可开枪击杀任意一名玩家。",
    color: "border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.2)] text-emerald-400",
    icon: <Zap className="w-5 h-5" />,
    tag: "神职 · 强力威慑"
  },
  狼人: {
    name: "狼人 (Werewolf)",
    desc: "夜里袭杀，白天煽动。每个夜晚与狼人同伴会合啃食一名好人玩家，白天在人群中隐藏身份并煽动投票。",
    color: "border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)] text-red-500",
    icon: <Skull className="w-5 h-5" />,
    tag: "狼队 · 暗夜袭杀者"
  },
  村民: {
    name: "村民 (Villager)",
    desc: "逻辑分析，多数表决。不具备特殊技能，主要通过在白天听取发言、推导逻辑并利用选票放逐狼人。",
    color: "border-slate-400 shadow-[0_0_15px_rgba(148,163,184,0.2)] text-slate-300",
    icon: <Users className="w-5 h-5" />,
    tag: "平民 · 逻辑基石"
  },
  平民: {
    name: "村民 (Villager)",
    desc: "逻辑分析，多数表决。不具备特殊技能，主要通过在白天听取发言、推导逻辑并利用选票放逐狼人。",
    color: "border-slate-400 shadow-[0_0_15px_rgba(148,163,184,0.2)] text-slate-300",
    icon: <Users className="w-5 h-5" />,
    tag: "平民 · 逻辑基石"
  }
};

export default function GameSetup() {
  const {
    starting,
    startError,
    setupStep,
    showSettingsModal,
    gameMode,
    boardMode,
    boardPresets,
    playableRoles,
    selectedPresetId,
    customLineup,
    presetsLoading,
    playerCount,
    userRole,
    humanSeat,
    hasSheriff,
    enableDeepGame,
    customizeModels,
    availableModels,
    modelsLoading,
    seatProviders,
    defaultProviderId,
    effectivePlayerCount,
    lineupRoleOptions,
    setSetupStep,
    setShowSettingsModal,
    setGameMode,
    setUserRole,
    setHumanSeat,
    setHasSheriff,
    setEnableDeepGame,
    setCustomizeModels,
    setCustomLineup,
    setSeatProviders,
    setAvailableModels,
    startMatch,
    handlePlayerCountChange,
    handleSelectPreset,
    handleBoardModeChange,
  } = useGameSetup();

  return (
    <div className="w-full h-full absolute inset-0 z-10 overflow-y-auto overflow-x-hidden custom-scrollbar transition-all duration-500">
      <div className={`w-full min-h-full ${setupStep === "settings" ? "max-w-4xl px-2 sm:px-4 mx-auto flex flex-col items-center justify-center py-12" : "max-w-[1400px] mx-auto flex items-center justify-start px-8 md:px-24 xl:px-40 py-12"} select-none relative bg-transparent`}>
        <AnimatePresence mode="wait">
          {setupStep === "landing" ? (
            <LandingPage onEnter={() => setSetupStep("settings")} />
          ) : (
            <SettingsPage
              gameMode={gameMode}
              onGameModeChange={setGameMode}
              boardMode={boardMode}
              onBoardModeChange={handleBoardModeChange}
              boardPresets={boardPresets}
              playableRoles={playableRoles}
              selectedPresetId={selectedPresetId}
              onSelectPreset={handleSelectPreset}
              customLineup={customLineup}
              onCustomLineupChange={setCustomLineup}
              playerCount={playerCount}
              onPlayerCountChange={handlePlayerCountChange}
              presetsLoading={presetsLoading}
              enableDeepGame={enableDeepGame}
              onToggleDeepGame={() => setEnableDeepGame((v) => !v)}
              hasSheriff={hasSheriff}
              onSheriffChange={setHasSheriff}
              customizeModels={customizeModels}
              onToggleCustomizeModels={() => setCustomizeModels((v) => !v)}
              modelsLoading={modelsLoading}
              availableModels={availableModels}
              seatProviders={seatProviders}
              onSeatProviderChange={(index, providerId) =>
                setSeatProviders((prev) => {
                  const next = [...prev];
                  next[index] = providerId;
                  return next;
                })
              }
              effectivePlayerCount={effectivePlayerCount}
              humanSeat={humanSeat}
              defaultProviderId={defaultProviderId}
              userRole={userRole}
              onUserRoleChange={setUserRole}
              onHumanSeatChange={setHumanSeat}
              lineupRoleOptions={lineupRoleOptions}
              onBack={() => setSetupStep("landing")}
              starting={starting}
              startError={startError}
              onStartGame={startMatch}
            />
          )}
        </AnimatePresence>

        {/* 右上角控件组：音量键 + 设置齿轮 —— 同一 flex 行，等高等大对齐、两步共用 */}
        <div className="fixed top-6 right-6 md:top-8 md:right-8 z-50 flex items-center gap-2.5">
          <AudioControls className="relative" />
          <button
            onClick={() => setShowSettingsModal(true)}
            className="flex items-center justify-center p-2 md:p-2.5 bg-zinc-900/60 border border-zinc-800/80 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 shadow-xl backdrop-blur-md transition-all active:scale-95"
          >
            <Settings className="w-5 h-5 md:w-6 md:h-6" />
          </button>
        </div>

        <ApiKeysSettingsModal
          open={showSettingsModal}
          onClose={() => {
            setShowSettingsModal(false);
            if (setupStep === "settings") {
              ApiClient.getAvailableModels()
                .then((data) => setAvailableModels(data.models))
                .catch(() => setAvailableModels([]));
            }
          }}
        />
      </div>
    </div>
  );
}

/* ─── Landing page ─── */
const LandingPage = React.memo(function _LandingPage({ onEnter }: { onEnter: () => void }) {
  return (
    <motion.div
      key="landing"
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -50, filter: "blur(4px)" }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className="w-full max-w-[20rem] p-4 lg:p-6 flex flex-col items-center sm:items-start text-center sm:text-left relative z-10"
    >
      <div className="w-12 h-12 rounded-full border border-amber-600/30 bg-amber-500/5 shadow-[0_0_50px_rgba(245,158,11,0.15)] flex items-center justify-center mb-8 relative">
        <Eye className="w-5 h-5 text-amber-500/80" />
        <div className="absolute inset-0 rounded-full border-[1px] border-amber-500/20 animate-ping" style={{ animationDuration: "3.5s" }} />
        <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-amber-500/60 rotate-45" />
        <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-amber-500/60 rotate-45" />
        <div className="absolute top-1/2 -left-2 -translate-y-1/2 w-1.5 h-1.5 bg-amber-500/60 rotate-45" />
        <div className="absolute top-1/2 -right-2 -translate-y-1/2 w-1.5 h-1.5 bg-amber-500/60 rotate-45" />
      </div>

      <div className="flex border-t border-b border-amber-600/30 py-2 mb-6 relative w-full justify-center sm:justify-start">
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-1 bg-amber-500/60 rotate-45 hidden sm:block" />
        <span className="text-[9px] text-amber-500/80 font-serif tracking-[0.2em] uppercase sm:pl-3">
          ~ 经典狼人杀 ∙ 智能大模型博弈 ~
        </span>
      </div>

      <h1 className="font-serif text-3xl lg:text-4xl font-medium text-transparent bg-clip-text bg-gradient-to-b from-amber-100 via-amber-300 to-amber-700 tracking-widest mb-2 drop-shadow-lg" style={{textShadow: "0 4px 20px rgba(245, 158, 11, 0.4)"}}>
        智能狼人杀
      </h1>
      <h2 className="font-gothic text-xl lg:text-2xl text-amber-500/60 tracking-[0.1em] mb-6 opacity-90 drop-shadow">
        The Artificial Intelligence
      </h2>

      <p className="text-[10px] lg:text-xs font-serif text-amber-50/70 tracking-[0.1em] leading-[2] max-w-[18rem] mb-8 opacity-90 relative">
        大语言模型驱动的人机对弈平台。<br/>
        亲临圆桌，扮演神职与群狼勾心斗角；<br/>
        退居幕后，开启上帝视角，静观推演。
      </p>

      <div className="w-full flex flex-col gap-3 relative z-20 mt-2">
        <button
          onClick={onEnter}
          className="relative w-full px-4 py-3 font-gothic text-amber-950 text-base lg:text-lg tracking-[0.15em] transition-all duration-300 rounded overflow-hidden group shadow-[0_0_20px_rgba(245,158,11,0.1)] hover:shadow-[0_0_40px_rgba(245,158,11,0.3)] active:translate-y-px"
          style={{ clipPath: "polygon(0 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%)" }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-amber-300 via-amber-500 to-yellow-700" />
          <div className="absolute inset-x-0 top-0 h-px bg-white/40" />
          <div className="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="absolute inset-0 rounded border border-amber-300/30 m-0.5 pointer-events-none" />
          <div className="relative flex items-center justify-center gap-2">
            <span className="font-serif font-black text-[10px] lg:text-xs uppercase tracking-[0.2em]">进入盘面</span>
            <span className="mx-1 opacity-60 font-serif text-[10px]">•</span>
            <span>Play</span>
          </div>
        </button>

        <Link
          to="/home"
          className="flex py-2.5 px-4 font-gothic text-sm lg:text-base rounded border border-amber-900/40 bg-black/40 text-amber-500/70 hover:text-amber-300 hover:bg-black/60 hover:border-amber-700/60 w-full transition-all items-center justify-center gap-2 cursor-pointer backdrop-blur-sm group"
          style={{ clipPath: "polygon(8px 0, 100% 0, 100% 100%, 0 100%, 0 8px)" }}
        >
          <Cpu className="w-3.5 h-3.5 group-hover:text-amber-400 transition-colors" />
          <span className="font-serif font-bold text-[10px] lg:text-xs tracking-[0.25em] uppercase">观测后台</span>
          <span className="mx-1 opacity-50 font-serif text-[10px]">•</span>
          <span>Dashboard</span>
        </Link>
      </div>
    </motion.div>
  );
})

/* ─── Settings page ─── */
const SettingsPage = React.memo(function _SettingsPage({
  gameMode, onGameModeChange,
  boardMode, onBoardModeChange,
  boardPresets, playableRoles, selectedPresetId, onSelectPreset,
  customLineup, onCustomLineupChange,
  playerCount, onPlayerCountChange,
  presetsLoading,
  enableDeepGame, onToggleDeepGame,
  hasSheriff, onSheriffChange,
  customizeModels, onToggleCustomizeModels,
  modelsLoading, availableModels, seatProviders, onSeatProviderChange,
  effectivePlayerCount, humanSeat, defaultProviderId,
  userRole, onUserRoleChange, onHumanSeatChange,
  lineupRoleOptions,
  onBack,
  starting, startError, onStartGame,
}: {
  gameMode: "llmOnly" | "humanVsAI";
  onGameModeChange: (m: "llmOnly" | "humanVsAI") => void;
  boardMode: "curated" | "standard" | "custom";
  onBoardModeChange: (m: "curated" | "standard" | "custom") => void;
  boardPresets: import("../api/types").BoardPresetOption[];
  playableRoles: import("../api/types").PlayableRoleOption[];
  selectedPresetId: string;
  onSelectPreset: (id: string) => void;
  customLineup: string[];
  onCustomLineupChange: (l: string[]) => void;
  playerCount: number;
  onPlayerCountChange: (n: number) => void;
  presetsLoading: boolean;
  enableDeepGame: boolean;
  onToggleDeepGame: () => void;
  hasSheriff: boolean;
  onSheriffChange: (v: boolean) => void;
  customizeModels: boolean;
  onToggleCustomizeModels: () => void;
  modelsLoading: boolean;
  availableModels: import("../api/types").AvailableModelOption[];
  seatProviders: string[];
  onSeatProviderChange: (i: number, pid: string) => void;
  effectivePlayerCount: number;
  humanSeat: number;
  defaultProviderId: string;
  userRole: string;
  onUserRoleChange: (r: string) => void;
  onHumanSeatChange: (s: number) => void;
  lineupRoleOptions: { key: string; label: string }[];
  onBack: () => void;
  starting: boolean;
  startError: string | null;
  onStartGame: () => void;
}) {
  return (
    <motion.div
      key="settings"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95, filter: "blur(4px)" }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-full relative tarot-card p-5 md:p-8 flex flex-col flex-grow md:flex-grow-0 my-8 text-slate-300 transform-gpu"
    >
      <div className="absolute inset-0 bg-woodcut-dark opacity-30 pointer-events-none mix-blend-overlay" />
      <div className="absolute top-3 left-3 w-4 h-4 border-t-[1px] border-l-[1px] border-amber-600/40 rounded-tl" />
      <div className="absolute top-3 right-3 w-4 h-4 border-t-[1px] border-r-[1px] border-amber-600/40 rounded-tr" />
      <div className="absolute bottom-3 left-3 w-4 h-4 border-b-[1px] border-l-[1px] border-amber-600/40 rounded-bl" />
      <div className="absolute bottom-3 right-3 w-4 h-4 border-b-[1px] border-r-[1px] border-amber-600/40 rounded-br" />

      <div className="w-full flex items-center justify-between border-b border-amber-900/40 pb-4 mb-6 relative z-10">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 rounded bg-black/40 border border-amber-900/30 text-[10px] text-amber-500/70 hover:text-amber-400 hover:border-amber-500/50 hover:bg-black/60 transition-all font-sans font-bold tracking-widest cursor-pointer active:scale-95"
        >
          ← 返 回 <span className="font-gothic text-xs ml-1">Back</span>
        </button>
        <div className="flex flex-col items-end">
          <span className="font-serif text-lg md:text-xl font-medium text-amber-500 tracking-[0.2em] uppercase drop-shadow-md">
            启示录 ∙ 规则仪轨
          </span>
          <span className="font-gothic text-xs text-amber-500/50 tracking-[0.2em] uppercase">
            Match Configuration
          </span>
        </div>
      </div>

      <div className="w-full flex flex-col lg:flex-row gap-6 lg:items-start relative z-10">
        {/* Left Column */}
        <div className="flex-1 flex flex-col gap-5 min-w-0">
          {/* Game mode */}
          <div className="flex flex-col gap-3">
            <span className="font-serif text-[11px] text-amber-500 font-bold tracking-[0.2em] flex items-center gap-2">
              <span className="font-gothic text-amber-700 text-sm">I.</span> 模式抉择{" "}
              <span className="font-gothic text-xs uppercase opacity-70 ml-1">Game Mode</span>
              <span className="inline-block h-px flex-grow bg-gradient-to-r from-amber-900/50 to-transparent ml-2" />
            </span>
            <div className="grid grid-cols-1 gap-3">
              <button
                type="button"
                onClick={() => onGameModeChange("humanVsAI")}
                className={`flex flex-col text-left p-4 rounded border transition-all duration-300 relative cursor-pointer group ${
                  gameMode === "humanVsAI" ? "bg-amber-900/20 border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.1)]" : "bg-black/40 border-slate-800 hover:bg-slate-900/80 hover:border-amber-900/40"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Shield className={`w-4 h-4 ${gameMode === "humanVsAI" ? "text-amber-500" : "text-slate-500"}`} />
                    <span className={`font-sans text-xs font-bold tracking-widest uppercase ${gameMode === "humanVsAI" ? "text-amber-400" : "text-slate-400"}`}>亲临圆桌对战</span>
                  </div>
                  {gameMode === "humanVsAI" && <div className="w-2 h-2 rounded-full bg-amber-500 shadow-[0_0_5px_rgba(245,158,11,0.8)] animate-pulse" />}
                </div>
                <p className="text-[10px] text-slate-500 leading-relaxed font-sans">你将作为席位之一加入对局，与大语言模型扮演的玩家斗智斗勇。</p>
              </button>
              <button
                type="button"
                onClick={() => onGameModeChange("llmOnly")}
                className={`flex flex-col text-left p-4 rounded border transition-all duration-300 relative cursor-pointer group ${
                  gameMode === "llmOnly" ? "bg-red-900/20 border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.1)]" : "bg-black/40 border-slate-800 hover:bg-slate-900/80 hover:border-red-900/40"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Cpu className={`w-4 h-4 ${gameMode === "llmOnly" ? "text-red-500" : "text-slate-500"}`} />
                    <span className={`font-sans text-xs font-bold tracking-widest uppercase ${gameMode === "llmOnly" ? "text-red-400" : "text-slate-400"}`}>上帝观战模式</span>
                  </div>
                  {gameMode === "llmOnly" && <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_5px_rgba(239,68,68,0.8)] animate-pulse" />}
                </div>
                <p className="text-[10px] text-slate-500 leading-relaxed font-sans">化身上帝视角，退居幕后，观察纯 AI 之间的自动推演和厮杀。</p>
              </button>
            </div>
          </div>

          {presetsLoading ? (
            <p className="text-[10px] text-zinc-500 font-sans px-1">加载席位配置…</p>
          ) : (
            <BoardSetupPanel
              mode={boardMode}
              onModeChange={onBoardModeChange}
              presets={boardPresets}
              playableRoles={playableRoles}
              selectedPresetId={selectedPresetId}
              onSelectPreset={onSelectPreset}
              customLineup={customLineup}
              onCustomLineupChange={onCustomLineupChange}
              playerCount={playerCount}
              onPlayerCountChange={onPlayerCountChange}
            />
          )}

          <SetupBrainSheriffPanel
            enableDeepGame={enableDeepGame}
            onToggleDeepGame={onToggleDeepGame}
            hasSheriff={hasSheriff}
            onSheriffChange={onSheriffChange}
          />
        </div>

        {/* Right Column */}
        <div className="flex-1 flex flex-col gap-6 min-w-0 lg:sticky lg:top-2 lg:self-start">
          <div className="flex flex-col gap-3 flex-grow">
            <span className="font-serif text-[11px] text-amber-500 font-bold tracking-[0.2em] flex items-center gap-2">
              <span className="font-gothic text-amber-700 text-sm">III.</span> 抽取底牌{" "}
              <span className="font-gothic text-xs uppercase opacity-70 ml-1">Your Role</span>
              <span className="inline-block h-px flex-grow bg-gradient-to-r from-amber-900/50 to-transparent ml-2" />
            </span>

            <div
              className="flex flex-col gap-3 transition-opacity duration-300"
              style={{
                opacity: gameMode === "humanVsAI" ? 1 : 0.3,
                pointerEvents: gameMode === "humanVsAI" ? "auto" : "none",
              }}
            >
              <div className="flex flex-col gap-4 bg-black/40 border border-slate-800 rounded p-4 relative overflow-hidden">
                <div className="w-full max-w-[180px] mx-auto aspect-[3/4] border-2 border-amber-900/50 rounded-lg overflow-hidden shadow-[0_0_24px_rgba(245,158,11,0.12)] relative bg-black/60">
                  <img
                    key={userRole}
                    src={getTarotImage(userRole)}
                    alt={userRole}
                    className="w-full h-full object-cover object-top"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black via-black/70 to-transparent px-3 py-3 pointer-events-none">
                    <span className="block text-center font-serif text-sm font-bold text-amber-200 tracking-widest">{userRole}</span>
                  </div>
                </div>

                <div className="flex flex-col gap-2 relative z-10 w-full">
                  <label className="text-[10px] text-amber-500/80 font-serif tracking-widest uppercase text-center">选择你的身份</label>
                  <select
                    value={userRole}
                    onChange={(e) => onUserRoleChange(e.target.value)}
                    className="bg-black/60 border border-amber-500/30 text-amber-100 px-4 py-3 text-sm font-bold select-none cursor-pointer focus:outline-none focus:border-amber-500 shadow-md transition-colors w-full outline-none appearance-none text-center"
                    style={{ boxShadow: "inset 0 0 10px rgba(0,0,0,0.8)" }}
                  >
                    {lineupRoleOptions.map((opt) => (
                      <option key={opt.key} value={opt.label}>{opt.label}</option>
                    ))}
                  </select>
                  {(() => {
                    const detail = roleDetails[userRole];
                    if (!detail) return null;
                    return (
                      <p className="text-[10px] text-zinc-400 font-sans leading-relaxed text-center px-1">
                        {detail.desc}
                      </p>
                    );
                  })()}
                  <span className="text-[9px] text-zinc-500 font-mono leading-relaxed text-center">
                    仅可选择本局阵容中包含的身份；其余席位由 AI 随机发牌。
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-2 bg-black/40 border border-slate-800 rounded p-4">
                <label className="text-[10px] text-amber-500/80 font-serif tracking-widest uppercase">入座席位 · Your Seat</label>
                <div className="flex items-center justify-between gap-3">
                  <button type="button" onClick={() => onHumanSeatChange(Math.max(1, humanSeat - 1))} className="w-9 h-9 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg select-none transition-all cursor-pointer text-slate-400 hover:text-amber-400">-</button>
                  <div className="flex flex-col items-center">
                    <span className="text-2xl font-serif font-black text-amber-500 leading-none">{humanSeat} 号</span>
                    <span className="text-[8px] text-slate-500 uppercase tracking-widest mt-1">共 {effectivePlayerCount} 席</span>
                  </div>
                  <button type="button" onClick={() => onHumanSeatChange(Math.min(effectivePlayerCount, humanSeat + 1))} className="w-9 h-9 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg select-none transition-all cursor-pointer text-slate-400 hover:text-amber-400">+</button>
                </div>
                <span className="text-[9px] text-zinc-500 font-mono leading-relaxed">
                  其余席位由大语言模型扮演；身份随机发牌。
                </span>
              </div>
            </div>

            <SetupModelPanel
              customizeModels={customizeModels}
              onToggleCustomizeModels={onToggleCustomizeModels}
              modelsLoading={modelsLoading}
              availableModels={availableModels}
              seatProviders={seatProviders}
              onSeatProviderChange={onSeatProviderChange}
              effectivePlayerCount={effectivePlayerCount}
              humanSeat={humanSeat}
              gameMode={gameMode}
              defaultProviderId={defaultProviderId}
            />
          </div>
        </div>
      </div>

      {/* Launch button */}
      <div className="w-full flex flex-col gap-3 mt-6 relative z-20">
        <button
          onClick={onStartGame}
          disabled={starting}
          className="relative w-full px-8 py-5 flex items-center justify-center font-serif text-amber-950 transition-all duration-300 rounded overflow-hidden group shadow-[0_0_20px_rgba(245,158,11,0.15)] hover:shadow-[0_0_40px_rgba(245,158,11,0.4)] active:translate-y-px disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none"
          style={{ clipPath: "polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%)" }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-amber-300 via-amber-500 to-yellow-700 opacity-90" />
          <div className="absolute inset-x-0 top-0 h-px bg-white/60" />
          <div className="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="absolute inset-0 rounded border border-amber-300/30 m-1 pointer-events-none" />
          <div className="relative flex items-center justify-center gap-3">
            <Play className="w-4 h-4 fill-amber-950 drop-shadow-sm group-hover:scale-110 transition-transform" />
            <span className="font-serif font-black text-sm uppercase tracking-[0.3em]">{starting ? "真灵召唤中" : "拨转命盘 ∙ 开启对局"}</span>
            <span className="mx-1 opacity-60 font-serif text-[10px]">•</span>
            <span className="font-gothic text-xl tracking-[0.1em]">{starting ? "Summoning" : "Launch Match"}</span>
          </div>
        </button>
        {startError && (
          <p className="mt-2 text-center text-[11px] font-mono text-red-400/90">开局失败：{startError}</p>
        )}
      </div>

      <div className="text-center font-mono text-[9px] text-amber-900/50 tracking-[0.2em] mt-6 uppercase relative z-20">
        — 棋盘浮雕将在入座后自适应折叠并载入 —
      </div>
    </motion.div>
  );
})
