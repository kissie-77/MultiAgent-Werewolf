import React, { useState } from "react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { Users, Shield, Cpu, Zap, Eye, Skull, Flame, ChevronLeft, ChevronRight, Play } from "lucide-react";

export default function GameSetup() {
  const resetGame = useGameStore((state) => state.resetGame);
  const isLoading = useGameStore((state) => state.isLoading);
  const setSetupCount = useGameStore((state) => state.setSetupCount);

  const [isConfiguring, setIsConfiguring] = useState(false);
  const [gameMode, setGameMode] = useState<"llmOnly" | "humanVsAI">("humanVsAI");
  const [playerCount, setPlayerCount] = useState<number>(6);
  const [userRole, setUserRole] = useState<"预言家" | "女巫" | "猎人" | "狼人" | "村民">("预言家");

  React.useEffect(() => {
    setSetupCount(playerCount);
  }, [playerCount, setSetupCount]);

  React.useEffect(() => {
    return () => {
      setSetupCount(null);
    };
  }, [setSetupCount]);

  const startMatch = async () => {
    // Pass startImmediately = true so the server launches directly to DAY_DEBATE
    setSetupCount(null);
    await resetGame(userRole, playerCount, gameMode, true);
  };

  const getRolesDescription = (count: number) => {
    if (count === 1) return "1 预言家 (无狼人，完全探索模式)";
    if (count === 2) return "1 狼人 | 1 预言家";
    if (count === 3) return "1 狼人 | 1 预言家 | 1 女巫";
    if (count === 4) return "1 狼人 | 1 预言家 | 1 女巫 | 1 忠良村民";
    
    const wolves = count <= 6 ? 2 : count <= 11 ? 3 : 4;
    const citizens = count - 3 - wolves; // Seer, Witch, Hunter = 3 special
    return `${wolves} 狼人 | 1 预言家 | 1 女巫 | 1 猎人 ${citizens > 0 ? `| ${citizens} 忠良村民` : ""}`;
  };

  const roleDetails = {
    预言家: {
      name: "预言神官 (Seer)",
      desc: "烛照本真，窥知宿命。每个夜晚可以查验一名玩家的真实阵营，是指引愚昧好人的明灯。",
      color: "border-yellow-600 shadow-yellow-950/40 text-yellow-500",
      icon: <Eye className="w-5 h-5" />,
      tag: "神职 · 阵营向导"
    },
    女巫: {
      name: "猩红女巫 (Witch)",
      desc: "掌控生死，药剂毒水。拥有一瓶能使死者复苏的圣水与一瓶见血封喉的毒药，是黑夜中无声的审判官。",
      color: "border-fuchsia-600 shadow-fuchsia-950/40 text-fuchsia-500",
      icon: <Shield className="w-5 h-5" />,
      tag: "神职 · 强力输出"
    },
    猎人: {
      name: "钢枪猎人 (Hunter)",
      desc: "临终枪声，执念爆头。在被公决流放或狼人咬死时（除被药毒死外），可以开枪射杀任意一名玩家。",
      color: "border-emerald-600 shadow-emerald-950/40 text-emerald-500",
      icon: <Zap className="w-5 h-5" />,
      tag: "神职 · 威慑流派"
    },
    狼人: {
      name: "荒野巨狼 (Werewolf)",
      desc: "夜行百鬼，伪装啃噬。每个夜晚与同伴会合啃食一名好人，白昼中隐藏在人群内挑拨离间。",
      color: "border-red-650 shadow-red-950/40 text-red-500",
      icon: <Skull className="w-5 h-5" />,
      tag: "狼队 · 暗夜伪装者"
    },
    村民: {
      name: "落暮村民 (Villager)",
      desc: "白昼明镜，赤手空拳。没有奇迹神力，只有一双辨明善恶的冷眸，用投票将恶狼公决流放。",
      color: "border-zinc-500 shadow-zinc-950/40 text-zinc-400",
      icon: <Users className="w-5 h-5" />,
      tag: "平民 · 逻辑基石"
    }
  };

  const handlePlayerCountChange = (val: number) => {
    const nextVal = Math.max(1, Math.min(16, val));
    setPlayerCount(nextVal);
    
    // Auto adjust player role if chosen role is unavailable due to low occupant count
    if (nextVal === 1) {
      setUserRole("预言家");
    } else if (nextVal === 2) {
      if (userRole !== "预言家" && userRole !== "狼人") {
        setUserRole("预言家");
      }
    } else if (nextVal === 3) {
      if (userRole === "猎人" || userRole === "村民") {
        setUserRole("预言家");
      }
    }
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
            style={{}}
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
              在大理石圆盘刻纹和微温烛台前，指派好人神职与狡黠狼队的黑夜较量。
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
            style={{}}
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
                规划神明席位与对决规模。席位数立即重置大理石圆盘。
              </p>
            </div>

            <div className="space-y-3.5">

                         {/* SEC 1: GAME MODE SELECTOR */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest flex items-center gap-2">
                  <span>Ⅰ. 对 决 模 式 (Game Mode)</span>
                  <span className="inline-block h-px flex-grow bg-zinc-900/40" />
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  
                  {/* Option A: Human Selector */}
                  <button
                    type="button"
                    onClick={() => setGameMode("humanVsAI")}
                    className={`flex flex-col text-left p-2 md:p-2.5 rounded border transition-all duration-200 relative cursor-pointer group ${
                      gameMode === "humanVsAI"
                        ? "bg-yellow-500/10 border-yellow-500 shadow-[0_0_12px_rgba(234,179,8,0.1)]"
                        : "bg-transparent border-zinc-900/45 hover:bg-zinc-900/10 hover:border-zinc-800"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <Shield className={`w-3 h-3 ${gameMode === "humanVsAI" ? "text-yellow-500 animate-pulse" : "text-zinc-500"}`} />
                      <span className={`font-serif text-[11px] font-black tracking-wider uppercase ${gameMode === "humanVsAI" ? "text-[#fcfcfc]" : "text-zinc-400 group-hover:text-zinc-200"}`}>
                        人机契约对战 (Human vs AI)
                      </span>
                    </div>
                    <p className="text-[8.5px] text-zinc-500 font-sans leading-relaxed">
                      你抽选一张底牌角色卡加入圆桌，配合其他 AI 盟友进行黑夜博弈与白昼公决投票。
                    </p>
                    {gameMode === "humanVsAI" && (
                      <span className="absolute top-1.5 right-2 text-[8px] text-yellow-500 font-mono">● Active</span>
                    )}
                  </button>

                  {/* Option B: Spectator Selector */}
                  <button
                    type="button"
                    onClick={() => setGameMode("llmOnly")}
                    className={`flex flex-col text-left p-2 md:p-2.5 rounded border transition-all duration-200 relative cursor-pointer group ${
                      gameMode === "llmOnly"
                        ? "bg-red-500/10 border-red-500/80 shadow-[0_0_12px_rgba(239,68,68,0.1)]"
                        : "bg-transparent border-zinc-900/45 hover:bg-zinc-900/10 hover:border-zinc-800"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <Cpu className={`w-3 h-3 ${gameMode === "llmOnly" ? "text-red-500 animate-pulse" : "text-zinc-500"}`} />
                      <span className={`font-serif text-[11px] font-black tracking-wider uppercase ${gameMode === "llmOnly" ? "text-[#fcfcfc]" : "text-zinc-400 group-hover:text-zinc-200"}`}>
                        纯LLM观战对决 (Pure AI Spectator)
                      </span>
                    </div>
                    <p className="text-[8.5px] text-zinc-500 font-sans leading-relaxed">
                      完全裁判观摩。多名 Gemini 强健智能个体接管圆桌辩局，你可以实时审视思路。
                    </p>
                    {gameMode === "llmOnly" && (
                      <span className="absolute top-1.5 right-2 text-[8px] text-red-500 font-mono">● Spectating</span>
                    )}
                  </button>

                </div>
              </div>

              {/* SEC 2: PLAYER COUNT STEPPER SELECTOR (1 - 16) */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest flex items-center gap-2">
                  <span>Ⅱ. 席 位 议 员 (Player Seats: 1 - 16)</span>
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
                    {[4, 6, 8, 12, 16].map((num) => (
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

                {/* dynamic dynamic rule indicator */}
                <div className="px-2.5 py-1 bg-transparent border border-[#a855f7]/15 rounded text-[9px] font-mono text-zinc-400 flex flex-col md:flex-row md:items-center justify-between gap-1">
                  <div className="flex items-center gap-1">
                    <span className="text-yellow-500">⚖️ 席位配置：</span>
                    <span className="text-purple-400 font-bold">{getRolesDescription(playerCount)}</span>
                  </div>
                  <div className="text-zinc-550 text-[8px]">
                    席位将以 3D 浮雕投影重置圆盘上的座椅支柱。
                  </div>
                </div>
              </div>

              {/* SEC 3: CHOOSE ROLE (ONLY IF HUMAN) */}
              <div 
                className="flex flex-col gap-1.5 transition-all duration-200"
                style={{
                  opacity: gameMode === "humanVsAI" ? 1 : 0.2,
                  pointerEvents: gameMode === "humanVsAI" ? "auto" : "none"
                }}
              >
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest flex items-center gap-2">
                  <span>Ⅲ. 宿 命 契 约 (Select Identity Card)</span>
                  {gameMode === "llmOnly" && <span className="text-[7.5px] text-[#ef4444] px-1 border border-red-950 bg-red-950/20 rounded font-bold ml-1 tracking-normal">Spectator Mode</span>}
                  <span className="inline-block h-px flex-grow bg-zinc-900/40" />
                </span>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                  {(["预言家", "女巫", "猎人", "村民", "狼人"] as const).map((role) => {
                    const details = roleDetails[role];
                    const active = userRole === role && gameMode === "humanVsAI";
                    
                    // Determine if the role is valid for current seat count
                    let isUnavailable = false;
                    let warningText = "";
                    if (playerCount === 1) {
                      isUnavailable = role !== "预言家";
                      warningText = "需首验";
                    } else if (playerCount === 2) {
                      isUnavailable = role !== "预言家" && role !== "狼人";
                      warningText = "限双星";
                    } else if (playerCount === 3) {
                      isUnavailable = role === "猎人" || role === "村民";
                      warningText = role === "猎人" ? "需5人+" : "需4人+";
                    } else if (playerCount === 4) {
                      isUnavailable = role === "猎人";
                      warningText = "需5人+";
                    }

                    return (
                      <button
                        key={role}
                        type="button"
                        disabled={isUnavailable}
                        onClick={() => setUserRole(role)}
                        className={`p-1.5 md:p-2 flex flex-col justify-between items-center text-center rounded border transition-all duration-300 relative min-h-[120px] group ${
                          isUnavailable
                            ? "opacity-25 bg-transparent border-zinc-900 cursor-not-allowed"
                            : active
                              ? `bg-yellow-500/10 border-double border-4 ${details.color}`
                              : "bg-transparent border-zinc-900/35 hover:bg-zinc-900/10 hover:border-zinc-800 cursor-pointer"
                        }`}
                      >
                        <div className="flex flex-col items-center">
                          <span className="text-[7.5px] text-zinc-500 font-mono tracking-wider mb-0.5 block">{details.tag}</span>
                          <div className={`p-1 rounded-full border border-zinc-900/40 bg-[#161226]/10 mb-1 [&_svg]:w-3.5 [&_svg]:h-3.5 ${active ? "scale-100 text-[#fcfcfc]" : "text-zinc-650 group-hover:text-zinc-400"}`}>
                            {details.icon}
                          </div>
                          <span className={`font-serif text-[10px] font-black tracking-wider block ${active ? "text-yellow-500" : "text-zinc-400 group-hover:text-zinc-200"}`}>
                            {role}
                          </span>
                        </div>

                        <p className={`text-[7.5px] mt-0.5 mb-1 font-sans leading-tight line-clamp-2 ${active ? "text-zinc-450" : "text-zinc-550"}`}>
                          {details.desc}
                        </p>

                        {isUnavailable ? (
                          <span className="text-[7px] bg-red-950/40 text-red-500 border border-red-900/60 px-1 py-0.2 rounded font-sans uppercase">
                            {warningText}
                          </span>
                        ) : active ? (
                          <span className="text-[7px] bg-yellow-950/30 text-yellow-500 border border-yellow-850/60 px-1 py-0.2 rounded font-sans scale-90 uppercase">
                            SELECTED
                          </span>
                        ) : null}
                      </button>
                    );
                  })}
                </div>
              </div>

            </div>

            {/* Action Button Segment */}
            <div className="mt-4 pt-3 border-t border-zinc-900/40 flex flex-col items-center w-full">
              <button
                onClick={startMatch}
                disabled={isLoading}
                className="stone-btn relative w-full md:w-2/3 px-5 py-3 font-serif font-black text-[#f5f5f5] text-xs md:text-sm uppercase tracking-[0.2em] transition-all duration-300 rounded shadow-xl flex items-center justify-center gap-2 cursor-pointer active:translate-y-1"
                style={{
                  clipPath: "polygon(4% 0%, 96% 0%, 100% 18%, 100% 100%, 0% 100%, 0% 18%)",
                }}
              >
                <div className="absolute inset-x-0 top-0 h-0.5 bg-zinc-500/30" />
                <Flame className="w-4 h-4 text-red-500 animate-pulse" />
                <span>开启宿命对决 (AWAWKEN JUDGEMENT)</span>
                <Flame className="w-4 h-4 text-red-500 animate-pulse" />
              </button>
              
              <div className="font-mono text-[7.5px] text-zinc-500/80 tracking-widest mt-1.5 uppercase">
                小道迷雾驱散，3D席座位将瞬间对焦至辩论区。
              </div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
