import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate } from "react-router-dom";
import { useGameStore } from "../store";
import { ApiClient } from "../api/client";
import { getCustomApiKey, setCustomApiKey, getOpenAIApiKey, setOpenAIApiKey, getGeminiApiKey, setGeminiApiKey, getClaudeApiKey, setClaudeApiKey, getDoubaoApiKey, setDoubaoApiKey } from "../lib/config";
import { motion, AnimatePresence } from "motion/react";
import { Users, Shield, Cpu, Zap, Eye, Skull, Flame, Settings, Play, Key } from "lucide-react";

import { getTarotImage } from "../utils/roles";

export default function GameSetup() {
  const setSetupCount = useGameStore((state) => state.setSetupCount);
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  // setupStep represents the startup screen flow phase
  const [setupStep, setSetupStep] = useState<"landing" | "settings">("landing");
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [gameMode, setGameMode] = useState<"llmOnly" | "humanVsAI">("humanVsAI");
  const [playerCount, setPlayerCount] = useState<number>(6);
  const [userRole, setUserRole] = useState<string>("预言家");
  const [humanSeat, setHumanSeat] = useState<number>(1);
  const [hasSheriff, setHasSheriff] = useState<boolean>(true);
  const [apiKey, setApiKey] = useState<string>("");
  const [openaiKey, setOpenaiKey] = useState<string>("");
  const [geminiKey, setGeminiKey] = useState<string>("");
  const [claudeKey, setClaudeKey] = useState<string>("");
  const [doubaoKey, setDoubaoKey] = useState<string>("");

  useEffect(() => {
    setApiKey(getCustomApiKey());
    setOpenaiKey(getOpenAIApiKey());
    setGeminiKey(getGeminiApiKey());
    setClaudeKey(getClaudeApiKey());
    setDoubaoKey(getDoubaoApiKey());
  }, []);

  const handleApiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setApiKey(val);
    setCustomApiKey(val);
  };

  const handleOpenaiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setOpenaiKey(val);
    setOpenAIApiKey(val);
  };

  const handleGeminiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setGeminiKey(val);
    setGeminiApiKey(val);
  };

  const handleClaudeKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setClaudeKey(val);
    setClaudeApiKey(val);
  };

  const handleDoubaoKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setDoubaoKey(val);
    setDoubaoApiKey(val);
  };

  React.useEffect(() => {
    setSetupCount(playerCount);
  }, [playerCount, setSetupCount]);

  // Keep the human seat within the current player-count range.
  React.useEffect(() => {
    setHumanSeat((seat) => Math.min(Math.max(1, seat), playerCount));
  }, [playerCount]);

  React.useEffect(() => {
    return () => {
      setSetupCount(null);
    };
  }, [setSetupCount]);

  useEffect(() => {
    if (setupStep !== "settings" || gameMode !== "llmOnly") return;
    let cancelled = false;
    setSpectateRunsLoading(true);
    ApiClient.getSpectatableRuns(1, 40)
      .then((data) => {
        if (cancelled) return;
        const rows = data.runs.items.map(mapRunRow).filter((r) => r.hasReplay);
        setSpectatableRuns(rows);
        setSpectateRunId((prev) => prev || rows[0]?.runId || "");
        setSpectateRunsError(null);
      })
      .catch((err) => {
        if (!cancelled) {
          setSpectateRunsError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => !cancelled && setSpectateRunsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [setupStep, gameMode]);

  const startMatch = async () => {
    if (starting) return;
    setStartError(null);
    setStarting(true);
    setSetupCount(null);
    try {
      const res = await ApiClient.startGame({
        config_id: "llm-6p-deepseek",
        // 把用户选的座位数传给后端（后端 resize_players_config 会按模板扩/缩到 N 座）；
        // 不传则永远只开 config 自带的 6 人局。范围对齐后端校验 6–20。
        player_count: playerCount,
        badge_flow: hasSheriff,
        // 人机模式下占用一个人类座位 + 把所选角色传给后端（后端会把该角色换到本座位）；
        // 纯观战模式不传 human。
        ...(gameMode === "humanVsAI" ? { human: { seat: humanSeat, role: userRole } } : {}),
      });
      // 人机模式：用后端返回的座位令牌进入本人座位视角；否则进上帝观战。
      if (gameMode === "humanVsAI" && res.player_token) {
        const sep = res.game_page_path.includes("?") ? "&" : "?";
        navigate(
          `${res.game_page_path}${sep}view=seat&seat=${humanSeat}&token=${encodeURIComponent(res.player_token)}`
        );
      } else {
        navigate(res.game_page_path); // "/game?run_id=...&source=runs"
      }
    } catch (e) {
      setStartError(e instanceof Error ? e.message : String(e));
      setStarting(false);
    }
  };

  const getRolesDescription = (count: number) => {
    if (count === 1) return "1 预言家 (无狼人，完全探索模式)";
    if (count === 2) return "1 狼人 | 1 预言家";
    if (count === 3) return "1 狼人 | 1 预言家 | 1 女巫";
    if (count === 4) return "1 狼人 | 1 预言家 | 1 女巫 | 1 村民";
    
    const wolves = count <= 6 ? 2 : count <= 11 ? 3 : 4;
    const citizens = count - 3 - wolves; // Seer, Witch, Hunter = 3 special roles
    return `${wolves} 狼人 | 1 预言家 | 1 女巫 | 1 猎人 ${citizens > 0 ? `| ${citizens} 村民` : ""}`;
  };

  const roleDetails = {
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
    }
  };

  const handlePlayerCountChange = (val: number) => {
    // Web API 仅支持 6–20 座（StartGameRequest.player_count: ge=6, le=20）；
    // 低于 6 的局后端会 422 拒绝，故在 UI 侧就把范围钳到 6–20。
    const nextVal = Math.max(6, Math.min(20, val));
    setPlayerCount(nextVal);
  };

  return (
    <div className={`w-full h-full absolute inset-0 z-10 overflow-y-auto overflow-x-hidden custom-scrollbar transition-all duration-500 ${setupStep === "settings" ? "" : ""}`}>
      <div className={`w-full min-h-full ${setupStep === "settings" ? "max-w-4xl px-2 sm:px-4 mx-auto flex flex-col items-center justify-center py-12" : "max-w-[1400px] mx-auto flex items-center justify-start px-8 md:px-24 xl:px-40 py-12"} select-none relative bg-transparent`}>
        <AnimatePresence mode="wait">
          {setupStep === "landing" ? (
          <motion.div
            key="landing"
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50, filter: "blur(4px)" }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="w-full max-w-[20rem] p-4 lg:p-6 flex flex-col items-center sm:items-start text-center sm:text-left relative z-10"
          >
            {/* Glowing Moon / Crest at Top */}
            <div className="w-12 h-12 rounded-full border border-amber-600/30 bg-amber-500/5 shadow-[0_0_50px_rgba(245,158,11,0.15)] flex items-center justify-center mb-8 relative">
              <Eye className="w-5 h-5 text-amber-500/80" />
              <div className="absolute inset-0 rounded-full border-[1px] border-amber-500/20 animate-ping" style={{ animationDuration: "3.5s" }} />
              {/* Tarot style diamond accents */}
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

            {/* Action Buttons Section */}
            <div className="w-full flex flex-col gap-3 relative z-20 mt-2">
              {/* Main Play Button */}
              <button
                onClick={() => setSetupStep("settings")}
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

              {/* Nav down to Home Page Dashboard */}
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
        ) : (
          <motion.div
            key="settings"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95, filter: "blur(4px)" }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="w-full relative tarot-card p-5 md:p-8 flex flex-col flex-grow md:flex-grow-0 my-8 text-slate-300 transform-gpu"
          >
            {/* Background texture layering */}
            <div className="absolute inset-0 bg-woodcut-dark opacity-30 pointer-events-none mix-blend-overlay" />
            
            {/* Corner Decorative Ornaments */}
            <div className="absolute top-3 left-3 w-4 h-4 border-t-[1px] border-l-[1px] border-amber-600/40 rounded-tl" />
            <div className="absolute top-3 right-3 w-4 h-4 border-t-[1px] border-r-[1px] border-amber-600/40 rounded-tr" />
            <div className="absolute bottom-3 left-3 w-4 h-4 border-b-[1px] border-l-[1px] border-amber-600/40 rounded-bl" />
            <div className="absolute bottom-3 right-3 w-4 h-4 border-b-[1px] border-r-[1px] border-amber-600/40 rounded-br" />

            {/* Header with back button */}
            <div className="w-full flex items-center justify-between border-b border-amber-900/40 pb-4 mb-6 relative z-10">
              <button
                onClick={() => setSetupStep("landing")}
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

            <div className="w-full flex flex-col lg:flex-row gap-6 relative z-10">
              {/* Left Column: Basic Settings */}
              <div className="flex-1 flex flex-col gap-6">
                {/* Ⅰ. 游戏模式 */}
                <div className="flex flex-col gap-3">
                  <span className="font-serif text-[11px] text-amber-500 font-bold tracking-[0.2em] flex items-center gap-2">
                    <span className="font-gothic text-amber-700 text-sm">I.</span> 模式抉择 <span className="font-gothic text-xs uppercase opacity-70 ml-1">Game Mode</span>
                    <span className="inline-block h-px flex-grow bg-gradient-to-r from-amber-900/50 to-transparent ml-2" />
                  </span>
                  <div className="grid grid-cols-1 gap-3">
                    <button
                      type="button"
                      onClick={() => setGameMode("humanVsAI")}
                      className={`flex flex-col text-left p-4 rounded border transition-all duration-300 relative cursor-pointer group ${
                        gameMode === "humanVsAI"
                          ? "bg-amber-900/20 border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.1)]"
                          : "bg-black/40 border-slate-800 hover:bg-slate-900/80 hover:border-amber-900/40"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Shield className={`w-4 h-4 ${gameMode === "humanVsAI" ? "text-amber-500" : "text-slate-500"}`} />
                          <span className={`font-sans text-xs font-bold tracking-widest uppercase ${gameMode === "humanVsAI" ? "text-amber-400" : "text-slate-400"}`}>
                            亲临圆桌对战
                          </span>
                        </div>
                        {gameMode === "humanVsAI" && (
                          <div className="w-2 h-2 rounded-full bg-amber-500 shadow-[0_0_5px_rgba(245,158,11,0.8)] animate-pulse" />
                        )}
                      </div>
                      <p className="text-[10px] text-slate-500 leading-relaxed font-sans">
                        你将作为席位之一加入对局，与大语言模型扮演的玩家斗智斗勇。
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setGameMode("llmOnly")}
                      className={`flex flex-col text-left p-4 rounded border transition-all duration-300 relative cursor-pointer group ${
                        gameMode === "llmOnly"
                          ? "bg-red-900/20 border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.1)]"
                          : "bg-black/40 border-slate-800 hover:bg-slate-900/80 hover:border-red-900/40"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Cpu className={`w-4 h-4 ${gameMode === "llmOnly" ? "text-red-500" : "text-slate-500"}`} />
                          <span className={`font-sans text-xs font-bold tracking-widest uppercase ${gameMode === "llmOnly" ? "text-red-400" : "text-slate-400"}`}>
                            上帝观战模式
                          </span>
                        </div>
                        {gameMode === "llmOnly" && (
                          <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_5px_rgba(239,68,68,0.8)] animate-pulse" />
                        )}
                      </div>
                      <p className="text-[10px] text-slate-500 leading-relaxed font-sans">
                        化身上帝视角，退居幕后，观察纯 AI 之间的自动推演和厮杀。
                      </p>
                    </button>
                  </div>
                </div>

                {/* Ⅱ. 游戏人数 */}
                <div className="flex flex-col gap-3">
                  <span className="font-serif text-[11px] text-amber-500 font-bold tracking-[0.2em] flex items-center gap-2">
                    <span className="font-gothic text-amber-700 text-sm">II.</span> 席位编排 <span className="font-gothic text-xs uppercase opacity-70 ml-1">Player Seats</span>
                    <span className="inline-block h-px flex-grow bg-gradient-to-r from-amber-900/50 to-transparent ml-2" />
                  </span>
                  
                  <div className="flex flex-col items-center gap-4 bg-black/40 border border-slate-800 p-4 rounded">
                    <div className="w-full flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => handlePlayerCountChange(playerCount - 1)}
                        className="w-10 h-10 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg select-none transition-all cursor-pointer text-slate-400 hover:text-amber-400"
                      >
                        -
                      </button>
                      
                      <div className="flex flex-col items-center">
                        <span className="text-3xl font-serif font-black text-amber-500 leading-none drop-shadow-[0_2px_4px_rgba(245,158,11,0.2)]">
                          {playerCount}
                        </span>
                        <span className="text-[8px] text-slate-500 uppercase tracking-widest mt-1">
                          入局玩家数量
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => handlePlayerCountChange(playerCount + 1)}
                        className="w-10 h-10 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg select-none transition-all cursor-pointer text-slate-400 hover:text-amber-400"
                      >
                        +
                      </button>
                    </div>

                    <div className="w-full flex flex-wrap items-center justify-center gap-2 pt-3 border-t border-slate-800/50">
                      {[6, 8, 9, 12].map((num) => (
                        <button
                          key={num}
                          type="button"
                          onClick={() => handlePlayerCountChange(num)}
                          className={`px-3 py-1.5 rounded text-[10px] font-mono font-bold border transition-all duration-300 cursor-pointer ${
                            playerCount === num
                              ? "bg-amber-500/20 text-amber-400 border-amber-500/50 shadow-[0_0_10px_rgba(245,158,11,0.15)]"
                              : "bg-transparent text-slate-500 border-slate-700 hover:text-amber-100 hover:border-amber-900/50 hover:bg-amber-900/10"
                          }`}
                        >
                          {num} 人局
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="px-4 py-3 bg-slate-900/60 border border-slate-800 rounded text-[10px] font-serif text-slate-400 flex flex-col gap-1.5 shadow-inner">
                    <div className="flex items-start gap-2">
                      <span className="text-amber-600/80 mt-0.5">⚖️</span>
                      <div>
                        <span className="text-slate-500 mr-2 uppercase tracking-wide text-[9px]">阵营配置:</span>
                        <span className="text-amber-100/90 font-bold">{getRolesDescription(playerCount)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Ⅳ. 警长选举 */}
                <div className="flex flex-col gap-3">
                  <span className="font-serif text-[11px] text-amber-500 font-bold tracking-[0.2em] flex items-center gap-2">
                    <span className="font-gothic text-amber-700 text-sm">IV.</span> 警长竞选 <span className="font-gothic text-xs uppercase opacity-70 ml-1">Sheriff</span>
                    <span className="inline-block h-px flex-grow bg-gradient-to-r from-amber-900/50 to-transparent ml-2" />
                  </span>
                  
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setHasSheriff(true)}
                      className={`flex-1 p-3 rounded border transition-all duration-300 font-sans text-[11px] tracking-widest font-bold uppercase ${
                        hasSheriff
                          ? "bg-amber-500/15 border-amber-500/50 text-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.1)]"
                          : "bg-black/40 border-slate-800 text-slate-500 hover:text-slate-300 hover:border-slate-700"
                      }`}
                    >
                      开启警徽流
                    </button>
                    <button
                      type="button"
                      onClick={() => setHasSheriff(false)}
                      className={`flex-1 p-3 rounded border transition-all duration-300 font-sans text-[11px] tracking-widest font-bold uppercase ${
                        !hasSheriff
                          ? "bg-indigo-500/15 border-indigo-500/50 text-indigo-400 shadow-[0_0_10px_rgba(99,102,241,0.1)]"
                          : "bg-black/40 border-slate-800 text-slate-500 hover:text-slate-300 hover:border-slate-700"
                      }`}
                    >
                      无警徽局
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Column: Roles and Launch Button */}
              <div className="flex-1 flex flex-col gap-6">
                {/* Ⅲ. 你的游戏底牌 */}
                <div 
                  className="flex flex-col gap-3 transition-opacity duration-300 flex-grow"
                  style={{
                    opacity: gameMode === "humanVsAI" ? 1 : 0.3,
                    pointerEvents: gameMode === "humanVsAI" ? "auto" : "none"
                  }}
                >
                  <span className="font-serif text-[11px] text-amber-500 font-bold tracking-[0.2em] flex items-center gap-2">
                    <span className="font-gothic text-amber-700 text-sm">III.</span> 抽取底牌 <span className="font-gothic text-xs uppercase opacity-70 ml-1">Your Role</span>
                    <span className="inline-block h-px flex-grow bg-gradient-to-r from-amber-900/50 to-transparent ml-2" />
                  </span>


                  <div className="flex flex-row items-stretch gap-4 h-full bg-black/40 border border-slate-800 rounded p-4 relative overflow-hidden">
                    {/* Tarot preview portrait */}
                    <div className="w-1/3 max-w-[140px] shrink-0 border-2 border-amber-900/40 rounded overflow-hidden shadow-inner relative">
                        <img 
                          src={getTarotImage(userRole)}
                          alt={userRole} 
                          className="w-full h-full object-cover object-top mix-blend-luminosity hover:mix-blend-normal transition-all"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent pointer-events-none"/>
                    </div>
                    
                    {/* Select Form */}
                    <div className="flex-1 flex flex-col justify-center gap-3 relative z-10 w-full outline-none">
                       <label className="text-[10px] text-amber-500/80 font-serif tracking-widest uppercase">Select Arcana</label>
                       <select
                         value={userRole}
                         onChange={(e) => setUserRole(e.target.value)}
                         className="bg-black/60 border border-amber-500/30 text-amber-100 px-4 py-3 text-sm font-bold select-none cursor-pointer focus:outline-none focus:border-amber-500 shadow-md transition-colors w-full break-words outline-none appearance-none"
                         style={{ boxShadow: "inset 0 0 10px rgba(0,0,0,0.8)" }}
                       >
                          {/* Only roles that actually exist in the basic lineup the Web
                              start uses (llm-6p-deepseek, resized 6–20). Picking a role
                              outside the lineup can't be honored, so it isn't offered. */}
                          <optgroup label="好人阵营">
                            <option value="预言家">预言家 (Seer)</option>
                            <option value="女巫">女巫 (Witch)</option>
                            <option value="猎人">猎人 (Hunter)</option>
                            <option value="村民">村民 (Villager)</option>
                          </optgroup>
                          <optgroup label="狼人阵营">
                            <option value="狼人">狼人 (Werewolf)</option>
                          </optgroup>
                       </select>
                       <span className="text-[10px] text-zinc-500 mt-2 font-mono leading-relaxed">
                         你的身份将固定为所选角色；其余席位由 AI 扮演、身份随机发牌。
                       </span>
                    </div>
                  </div>

                  {/* Seat selection: which chair the human occupies (role is random). */}
                  <div className="flex flex-col gap-2 bg-black/40 border border-slate-800 rounded p-4">
                    <label className="text-[10px] text-amber-500/80 font-serif tracking-widest uppercase">
                      入座席位 · Your Seat
                    </label>
                    <div className="flex items-center justify-between gap-3">
                      <button
                        type="button"
                        onClick={() => setHumanSeat((s) => Math.max(1, s - 1))}
                        className="w-9 h-9 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg select-none transition-all cursor-pointer text-slate-400 hover:text-amber-400"
                      >
                        -
                      </button>
                      <div className="flex flex-col items-center">
                        <span className="text-2xl font-serif font-black text-amber-500 leading-none">
                          {humanSeat} 号
                        </span>
                        <span className="text-[8px] text-slate-500 uppercase tracking-widest mt-1">
                          共 {playerCount} 席
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setHumanSeat((s) => Math.min(playerCount, s + 1))}
                        className="w-9 h-9 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg select-none transition-all cursor-pointer text-slate-400 hover:text-amber-400"
                      >
                        +
                      </button>
                    </div>
                    <span className="text-[9px] text-zinc-500 font-mono leading-relaxed">
                      其余席位由大语言模型扮演；身份随机发牌。
                    </span>
                  </div>
              </div>
              </div>
            </div>
            
            {/* Launch Match Button */}
            <div className="w-full flex flex-col gap-3 mt-6 relative z-20">
              <button
                onClick={startMatch}
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
                <p className="mt-2 text-center text-[11px] font-mono text-red-400/90">
                  开局失败：{startError}
                </p>
              )}
            </div>

            <div className="text-center font-mono text-[9px] text-amber-900/50 tracking-[0.2em] mt-6 uppercase relative z-20">
              — 棋盘浮雕将在入座后自适应折叠并载入 —
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => setShowSettingsModal(true)}
        className="fixed top-6 right-6 md:top-8 md:right-8 z-50 p-2 md:p-2.5 bg-zinc-900/60 border border-zinc-800/80 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 shadow-xl backdrop-blur-md transition-all active:scale-95"
      >
        <Settings className="w-5 h-5 md:w-6 md:h-6" />
      </button>

      {/* Settings Modal */}
      {createPortal(
        <AnimatePresence>
          {showSettingsModal && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 select-none">
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                className="w-full max-w-md bg-slate-950 bg-woodcut-dark border border-amber-900/40 p-6 md:p-8 rounded-xl relative shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden"
              >
              {/* Corner Ornaments */}
              <div className="absolute top-2 left-2 w-3 h-3 border-t border-l border-amber-600/40" />
              <div className="absolute top-2 right-2 w-3 h-3 border-t border-r border-amber-600/40" />
              <div className="absolute bottom-2 left-2 w-3 h-3 border-b border-l border-amber-600/40" />
              <div className="absolute bottom-2 right-2 w-3 h-3 border-b border-r border-amber-600/40" />

              <button
                onClick={() => setShowSettingsModal(false)}
                className="absolute top-4 right-4 text-slate-500 hover:text-amber-500 transition-colors p-1 z-10"
              >
                ✕
              </button>
              
              <h2 className="text-lg font-serif font-black text-amber-500 uppercase tracking-widest mb-6 border-b border-amber-900/30 pb-3 flex items-center gap-2 relative z-10 drop-shadow-md">
                <Settings className="w-5 h-5 text-amber-600" />
                枢纽引擎 ∙ 密钥档案
              </h2>

              <div className="flex flex-col gap-5 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar relative z-10">
                <div className="flex flex-col gap-2">
                  <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Key className="w-4 h-4 text-amber-500/80" /> DEEPSEEK API KEY
                  </label>
                  <div className="flex items-center gap-2 bg-black/60 border border-slate-800 hover:border-amber-900/50 focus-within:border-amber-500/50 focus-within:bg-black/80 p-2 rounded transition-colors shadow-inner">
                    <input 
                      type="password"
                      placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
                      value={apiKey}
                      onChange={handleApiKeyChange}
                      className="bg-transparent border-none outline-none font-mono text-amber-100 text-xs flex-grow w-full placeholder:text-slate-700"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Key className="w-4 h-4 text-green-500/80" /> OPENAI API KEY
                  </label>
                  <div className="flex items-center gap-2 bg-black/60 border border-slate-800 hover:border-amber-900/50 focus-within:border-amber-500/50 focus-within:bg-black/80 p-2 rounded transition-colors shadow-inner">
                    <input 
                      type="password"
                      placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
                      value={openaiKey}
                      onChange={handleOpenaiKeyChange}
                      className="bg-transparent border-none outline-none font-mono text-amber-100 text-xs flex-grow w-full placeholder:text-slate-700"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Key className="w-4 h-4 text-blue-500/80" /> GEMINI API KEY
                  </label>
                  <div className="flex items-center gap-2 bg-black/60 border border-slate-800 hover:border-amber-900/50 focus-within:border-amber-500/50 focus-within:bg-black/80 p-2 rounded transition-colors shadow-inner">
                    <input 
                      type="password"
                      placeholder="AIza-xxxxxxxxxxxxxxxxxxxxxxxx"
                      value={geminiKey}
                      onChange={handleGeminiKeyChange}
                      className="bg-transparent border-none outline-none font-mono text-amber-100 text-xs flex-grow w-full placeholder:text-slate-700"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Key className="w-4 h-4 text-purple-500/80" /> CLAUDE API KEY
                  </label>
                  <div className="flex items-center gap-2 bg-black/60 border border-slate-800 hover:border-amber-900/50 focus-within:border-amber-500/50 focus-within:bg-black/80 p-2 rounded transition-colors shadow-inner">
                    <input 
                      type="password"
                      placeholder="sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx"
                      value={claudeKey}
                      onChange={handleClaudeKeyChange}
                      className="bg-transparent border-none outline-none font-mono text-amber-100 text-xs flex-grow w-full placeholder:text-slate-700"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="font-sans text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Key className="w-4 h-4 text-red-500/80" /> DOUBAO API KEY
                  </label>
                  <div className="flex items-center gap-2 bg-black/60 border border-slate-800 hover:border-amber-900/50 focus-within:border-amber-500/50 focus-within:bg-black/80 p-2 rounded transition-colors shadow-inner">
                    <input 
                      type="password"
                      placeholder="xxxxxxxxxxxxxxxxxxxxxxxx"
                      value={doubaoKey}
                      onChange={handleDoubaoKeyChange}
                      className="bg-transparent border-none outline-none font-mono text-amber-100 text-xs flex-grow w-full placeholder:text-slate-700"
                    />
                  </div>
                </div>

                <p className="text-[10px] text-slate-500 leading-relaxed font-sans mt-3 border-l-2 border-amber-900/50 pl-3">
                  配置各平台密钥以供大模型法阵运转。<br/>
                  * 符文信息仅存于本地浏览器，隐秘且安全。
                </p>
              </div>

              <div className="mt-8 pt-4 border-t border-amber-900/30 flex justify-end relative z-10">
                <button
                  onClick={() => setShowSettingsModal(false)}
                  className="px-6 py-2.5 bg-amber-950/40 border border-amber-600/50 text-amber-500 font-sans font-black text-xs uppercase tracking-widest hover:bg-amber-900/60 hover:text-amber-400 transition-all rounded"
                >
                  铭刻设定 (SAVE)
                </button>
              </div>
            </motion.div>
          </div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </div>
    </div>
  );
}
