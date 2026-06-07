import React, { useState } from "react";
import { createPortal } from "react-dom";
import { useGameStore } from "../store";
import { Send, Play, RefreshCw, Skull, Shield, Eye, Flame, ChevronDown, ChevronUp, BookOpen, X, Crown, EyeOff } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { getRoleImage } from "../utils/roles";
import SkillBar from "./SkillBar";
import { SkillReleaseModal } from "./SkillReleaseModal";

const TombstoneButton = ({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`stone-btn relative px-4 py-1.5 font-sans font-black text-[#f5f5f5] uppercase tracking-widest transition-all duration-300 rounded shadow-lg flex items-center gap-2 ${
      disabled
        ? "opacity-45 cursor-not-allowed select-none saturate-50"
        : "hover:scale-105 active:translate-y-1"
    }`}
    style={{
      clipPath: "polygon(5% 0%, 95% 0%, 100% 15%, 100% 100%, 0% 100%, 0% 15%)",
    }}
  >
    <div className="absolute inset-x-0 top-0 h-1 bg-zinc-500/30" />
    <span className="absolute top-1 left-2 text-[8px] text-zinc-400 select-none">🕀</span>
    <span className="absolute bottom-1 right-2 text-[8px] text-zinc-400 select-none">✝</span>
    {children}
  </button>
);

const ParchmentButton = ({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`relative px-4 py-1.5 font-mono font-bold text-zinc-950 bg-amber-100/90 border-2 border-amber-900 transition-all duration-300 rounded shadow-[3px_3px_0px_#451a03] flex items-center gap-1.5 ${
      disabled
        ? "opacity-50 cursor-not-allowed bg-zinc-800 text-zinc-600 border-zinc-950"
        : "hover:bg-amber-50 hover:shadow-[1px_1px_0px_#451a03] hover:translate-x-0.5 hover:translate-y-0.5 active:translate-y-1"
    }`}
    style={{
      borderRadius: "4px 12px 4px 12px"
    }}
  >
    <span className="absolute -top-1 left-4 text-[8px] opacity-40">〰</span>
    <span className="absolute bottom-0 right-3 text-[10px] opacity-30">∿</span>
    {children}
  </button>
);

const ActionTargetSelector = ({ 
  actionName, 
  actionIcon, 
  eligiblePlayers, 
  onConfirm,
  onClose,
  themeColor = "yellow",
  actionPrefix = "释放技能",
  actionPrompt = "请在下方悬赏序列选取您的目标："
}: { 
  actionName: string, 
  actionIcon: React.ReactNode, 
  eligiblePlayers: any[], 
  onConfirm: (targetId: number) => void,
  onClose?: () => void,
  themeColor?: "yellow" | "fuchsia" | "emerald" | "red" | "amber",
  actionPrefix?: string,
  actionPrompt?: string
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectedCardId = useGameStore((state) => state.selectedCardId);

  const handleSelect = (id: number) => {
    useGameStore.getState().setSelectedCardId(id);
  };

  const buttonActiveThemes = {
    yellow: "bg-yellow-500 text-black border-yellow-500",
    fuchsia: "bg-fuchsia-600 text-white border-fuchsia-500",
    emerald: "bg-emerald-600 text-white border-emerald-500",
    red: "bg-red-600 text-white border-red-500",
    amber: "bg-gradient-to-b from-amber-600 to-amber-800 text-amber-50 border-amber-500/50 hover:brightness-110"
  };

  // 计算塔罗牌逻辑
  const sessionRole = useGameStore((state) => state.state)?.players?.find((p: any) => p.isUser)?.role || "村民";
  const imageSrc = getRoleImage(sessionRole);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={`flex items-center gap-2 px-4 py-2 font-sans font-black text-xs uppercase tracking-[0.2em] transition-all duration-300 rounded border-2 shadow-lg hover:scale-105 active:scale-95 ${buttonActiveThemes[themeColor]} mix-blend-screen opacity-90 hover:opacity-100`}
      >
        {actionIcon} {actionPrefix}: {actionName}
      </button>

      {createPortal(
        <AnimatePresence>
          {isOpen && (
            <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center p-4 bg-black/80 backdrop-blur-md pointer-events-auto overflow-y-auto">
              <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                className="flex flex-col items-center relative w-full max-w-xl !overflow-visible my-auto"
              >
                <button 
                  onClick={() => {
                    setIsOpen(false);
                    if(onClose) onClose();
                  }}
                  className="absolute -top-6 right-0 md:-right-6 text-amber-900/60 hover:text-amber-500 transition-colors z-[110] hover:rotate-90 duration-300"
                >
                  <X className="w-8 h-8" />
                </button>

                {/* Full Tarot Card Image */}
                <div className="w-[180px] h-[306px] sm:w-[220px] sm:h-[374px] relative rounded-lg shadow-[0_0_60px_rgba(245,158,11,0.2)] flex flex-col items-center justify-center overflow-hidden z-20 mb-4 border border-amber-900/50 flex-shrink-0">
                    <img 
                      src={imageSrc}
                      alt={sessionRole}
                      className="w-full h-full object-cover object-center filter contrast-[1.1] saturate-75"
                    />
                    {/* Subtle overlay glare */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent pointer-events-none" />
                </div>
                
                <div className="text-center mb-4 relative z-20 flex-shrink-0">
                   <div className="flex items-center justify-center gap-2 mb-1.5 opacity-80">
                     <div className="w-1 h-1 bg-amber-500/60 rotate-45" />
                     <span className="font-serif text-[9px] uppercase tracking-[0.25em] text-amber-500/80">
                       ARCANA DECISION
                     </span>
                     <div className="w-1 h-1 bg-amber-500/60 rotate-45" />
                   </div>
                   
                   <h2 className="font-serif text-2xl lg:text-3xl font-medium text-transparent bg-clip-text bg-gradient-to-b from-amber-100 via-amber-300 to-amber-700 tracking-[0.1em] drop-shadow-md mb-1">
                     [ {actionPrefix} : {actionName} ]
                   </h2>
                   <span className="text-[10px] text-amber-900/60 font-mono tracking-widest">{actionPrompt}</span>
                </div>
                
                <div className="flex flex-wrap items-center justify-center gap-3 w-full mb-6 relative z-20 flex-shrink-0">
                  {eligiblePlayers.length === 0 ? (
                    <span className="text-amber-900/50 text-sm font-serif italic py-4 tracking-[0.2em]">— 没有可用灵魂 —</span>
                  ) : (
                    eligiblePlayers.map(p => {
                      const isSelected = p.id === selectedCardId;
                      
                      return (
                        <button
                          key={p.id}
                          onClick={() => handleSelect(p.id)}
                          className={`flex flex-col items-center justify-center w-[64px] h-[86px] rounded transition-all duration-300 cursor-pointer font-serif border-2 overflow-hidden relative group transform-gpu ${
                            isSelected 
                              ? "bg-amber-600/20 text-white border-amber-500/80 shadow-[0_0_15px_rgba(245,158,11,0.4)] scale-105" 
                              : "bg-[#0c0808] border-amber-900/30 text-amber-700/60 hover:border-amber-600/50 hover:bg-[#150d0d] hover:-translate-y-1 hover:shadow-lg hover:text-amber-500"
                          }`}
                        >
                          <div className="absolute inset-0 bg-woodcut-dark opacity-30 group-hover:opacity-40 transition-opacity" />
                          <span className={`text-xl font-black leading-none mb-1 relative z-10 ${isSelected ? "drop-shadow-md text-amber-100" : ""}`}>
                            {p.id}
                          </span>
                          <span className={`text-[8px] truncate max-w-[50px] tracking-widest relative z-10 ${isSelected ? "text-amber-200" : "opacity-60"}`}>{p.name}</span>
                          {isSelected && (
                             <div className="absolute bottom-0 w-full h-1 bg-amber-500/80" />
                          )}
                        </button>
                      )
                    })
                  )}
                </div>
                
                <div className="w-full flex justify-center relative z-20 flex-shrink-0 pb-4">
                  <button
                    onClick={() => {
                      setIsOpen(false);
                      onConfirm(selectedCardId!);
                    }}
                    disabled={!selectedCardId || !eligiblePlayers.find(p => p.id === selectedCardId)}
                    className={`relative px-12 py-3.5 font-black font-serif text-xs tracking-[0.3em] uppercase rounded transition-all duration-300 flex items-center justify-center overflow-hidden border ${
                      !selectedCardId || !eligiblePlayers.find(p => p.id === selectedCardId)
                        ? "bg-[#0c0808] text-amber-900/30 cursor-not-allowed border-amber-900/20"
                        : "bg-gradient-to-r from-[#201008] via-[#3a1d0f] to-[#201008] text-amber-500 border-amber-500/50 hover:scale-105 hover:shadow-[0_0_20px_rgba(245,158,11,0.3)] shadow-lg hover:text-amber-300 active:scale-95 cursor-pointer"
                    }`}
                  >
                    <div className="absolute inset-0 bg-woodcut pointer-events-none opacity-20" />
                    <span className="relative z-10 flex items-center gap-2">确 认 执 行</span>
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  )
}

const SealButton = ({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`relative w-28 h-28 flex flex-col items-center justify-center font-sans font-black text-center text-red-100 rounded-full bg-red-800 border-4 border-red-950 shadow-[0_6px_14px_rgba(239,68,68,0.3)] transition-all duration-300 transform ${
      disabled
        ? "opacity-40 cursor-not-allowed scale-95 saturate-50"
        : "hover:scale-110 hover:bg-red-700 hover:rotate-6 active:scale-95"
    }`}
  >
    {/* Wax drip circles */}
    <div className="absolute -inset-1 rounded-full border border-red-500/30 pointer-events-none" />
    <div className="absolute bottom-2 inset-x-4 h-1.5 bg-red-900/60 rounded-full blur-xs" />
    <span className="text-xl leading-none">⛧</span>
    <span className="text-[10px] tracking-widest font-extrabold uppercase mt-1">
      {children}
    </span>
    <span className="text-[7.5px] text-red-300/80 font-mono tracking-tighter uppercase mt-0.5">
      Seal Fate
    </span>
  </button>
);

export default function ControlPanel() {
  const gameState = useGameStore((state) => state.state);
  const selectedCardId = useGameStore((state) => state.selectedCardId);
  const userSpeechText = useGameStore((state) => state.userSpeechText);
  const setUserSpeechText = useGameStore((state) => state.setUserSpeechText);
  const submitUserSpeech = useGameStore((state) => state.submitUserSpeech);
  const castVote = useGameStore((state) => state.castVote);
  const simulateNextAI = useGameStore((state) => state.simulateNextAI);
  const nightSkillAction = useGameStore((state) => state.nightSkillAction);
  const transitionToDebate = useGameStore((state) => state.transitionToDebate);
  const resetGame = useGameStore((state) => state.resetGame);
  const isAutoPlaying = useGameStore((state) => state.isAutoPlaying);
  const toggleAutoPlay = useGameStore((state) => state.toggleAutoPlay);
  const setTargetingSkill = useGameStore((state) => state.setTargetingSkill);

  const WOLF_CAMP = ["狼人", "狼王", "白狼", "狼美人", "守卫狼", "隐狼", "血月使徒", "梦魇狼"];

  const [chosenRole, setChosenRole] = useState<string>("预言家");
  const [isSkillModalOpen, setIsSkillModalOpen] = useState(false);
  const [skillModalOpen, setSkillModalOpen] = useState(false);

  React.useEffect(() => {
    if (!gameState) return;
    
    // 自动播放逻辑触发，但带有轻微延迟
    const timer = setTimeout(() => {
      if (!isAutoPlaying) return; // 暂停时等待

      const { phase, currentSpeakerId, players } = gameState;
      
      const user = players.find(p => p.isUser);
      const isDead = user ? !user.isAlive : true; // LLM 模式下用户未定义，因此 isDead 为 true
      
      if (typeof currentSpeakerId === "number" && currentSpeakerId !== 1 && (phase === "DAY_DEBATE" || phase === "DAY_SHERIFF_RUN")) {
        simulateNextAI();
      } else if (phase === "DAY_VOTE" && (!user || isDead)) {
        // 如果是 LLM 模式或用户已死亡，自动跳过投票
        castVote();
      } else if (phase === "DAY_SHERIFF_VOTE" && (!user || isDead)) {
        useGameStore.getState().castSheriffVote(null);
      } else if (phase === "NIGHT_WOLF" && (!user || !WOLF_CAMP.includes(user.role) || isDead)) {
        nightSkillAction("NIGHT_KILL", 0);
      } else if (phase === "NIGHT_SEER" && (!user || user.role !== "预言家" || isDead)) {
        nightSkillAction("NIGHT_INSPECT", 0);
      } else if (phase === "NIGHT_WITCH" && (!user || user.role !== "女巫" || isDead)) {
        nightSkillAction("NIGHT_SAVED_OR_POISON", 0, { saved: false, poisonTarget: null });
      } else if (phase === "DAY_ANNOUNCEMENT") {
        transitionToDebate();
      }

    }, 3500); // 等待 3.5 秒让用户阅读文本

    return () => clearTimeout(timer);
  }, [gameState, isAutoPlaying, simulateNextAI, castVote, nightSkillAction, transitionToDebate]);

  if (!gameState) return null;

  const phase = gameState.phase;
  const user = gameState.players.find((p) => p.isUser);
  const isDead = user ? !user.isAlive : false;
  const victimId = gameState.victimId;

  // 确定技能状态
  const isNightWolf = phase === "NIGHT_WOLF" && !isDead && WOLF_CAMP.includes(user?.role || "");
  const isNightSeer = phase === "NIGHT_SEER" && !isDead && user?.role === "预言家";
  const isNightWitch = phase === "NIGHT_WITCH" && !isDead && user?.role === "女巫";
  const isDeadHunter = isDead && user?.role === "猎人" && !(gameState as any).hunterHasShot;

  const canUseSkill = isNightWolf || isNightSeer || isNightWitch || isDeadHunter;

  // 技能映射用于弹窗
  const getSkillConfig = () => {
    if (isNightWolf) return { actionName: "袭击目标", icon: "🐺", confirm: (id: number) => nightSkillAction("NIGHT_KILL", id) };
    if (isNightSeer) return { actionName: "预言查验", icon: "🔮", confirm: (id: number) => nightSkillAction("NIGHT_INSPECT", id) };
    if (isNightWitch) return { actionName: "投设毒药", icon: "💀", confirm: (id: number) => nightSkillAction("NIGHT_SAVED_OR_POISON", id, { saved: false, poisonTarget: id }) };
    if (isDeadHunter) return { actionName: "猎人开枪", icon: "🎯", confirm: (id: number) => nightSkillAction("HUNTER_SHOOT", id) };
    return { actionName: "无技能可用", icon: "🔥", confirm: () => {} };
  };

  const skillConfig = getSkillConfig();
  const PotionButton = ({ onClick, type, children, disabled }: { onClick: () => void; type: "elixir" | "poison"; children: React.ReactNode; disabled?: boolean }) => {
    // 毒药发出绿色/荧光黄光芒，解药发出霓虹紫/粉色光芒
    const glowColor = type === "elixir" ? "shadow-fuchsia-500/40 border-fuchsia-500" : "shadow-emerald-500/40 border-emerald-500";
    const liquidColor = type === "elixir" ? "bg-fuchsia-600" : "bg-emerald-600";
    const hoverColor = type === "elixir" ? "hover:bg-fuchsia-100/10" : "hover:bg-emerald-100/10";

    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className={`relative w-20 h-24 flex flex-col items-center justify-end pb-3 rounded border-2 bg-zinc-950/95 shadow-md transition-all duration-300 ${glowColor} ${hoverColor} ${
          disabled
            ? "opacity-30 cursor-not-allowed border-zinc-800 shadow-none scale-95"
            : "hover:-translate-y-2 hover:scale-105 active:translate-y-0"
        }`}
      >
        {/* Potion neck/cork stopper */}
        <div className="absolute -top-3 w-4 h-3 bg-yellow-900 border border-zinc-950 rounded-sm" />
        <div className="absolute -top-1 w-6 h-1 bg-zinc-800" />
        
        {/* Liquid filling wave animation */}
        <div className={`absolute bottom-0 inset-x-0 h-10 ${liquidColor} rounded-b transition-all duration-500 overflow-hidden`}>
          <div className="absolute top-0 inset-x-0 h-1.5 bg-white/20 animate-pulse" />
        </div>

        {/* Bubble particles */}
        <div className="absolute top-4 w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" />
        <div className="absolute top-6 right-5 w-1 h-1 bg-white/30 rounded-full animate-bounce delay-100" />

        <span className={`relative z-10 font-sans font-extrabold text-[9px] uppercase tracking-wider ${
          type === "elixir" ? "text-fuchsia-300" : "text-emerald-300"
        }`}>
          {children}
        </span>
      </button>
    );
  };

  return (
    <div className="bg-transparent px-6 py-2 flex flex-col gap-2 relative z-10 shrink-0 select-none justify-center">

      {/* Dynamic Interactive Skill & Spell Modal Overlay */}
      {createPortal(
        <AnimatePresence>
          {isSkillModalOpen && phase !== "ROLE_CHOICE" && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-8 bg-black/80 backdrop-blur-sm pointer-events-auto select-none"
            >
              <motion.div 
                initial={{ scale: 0.95, opacity: 0, y: 10 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.95, opacity: 0, y: 10 }}
                className="bg-slate-900 border border-indigo-500/30 bg-woodcut-dark backdrop-blur-md shadow-[0_0_40px_rgba(30,58,138,0.3)] rounded-2xl max-w-4xl w-full max-h-[85vh] overflow-y-auto relative flex flex-col"
              >
                <button 
                   onClick={() => setIsSkillModalOpen(false)}
                   className="absolute top-3 right-3 text-zinc-500 hover:text-red-400 bg-zinc-900 hover:bg-red-950 border border-zinc-800 p-2 rounded-full transition-colors z-20"
                >
                   <X className="w-4 h-4" />
                </button>
                <div className="p-4 sm:p-8">
                    <SkillBar hideHeader={false} />
                    
                    <div className="mt-8 flex justify-center">
                      <TombstoneButton onClick={() => setIsSkillModalOpen(false)}>
                         关闭祈祷席
                      </TombstoneButton>
                    </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}

      {/* Night and dead actions notification banner */}
      {isDead && phase !== "GAME_OVER" && (
        <div className="p-3 bg-red-950/15 border border-red-500/35 rounded text-center my-1 leading-relaxed">
          <span className="font-serif text-lg text-red-500 mr-2">☠</span>
          <span className="font-mono text-[#e0e0e0] text-xs font-black uppercase tracking-widest">
            你被放逐/吞噬，灵魂已归尘土。目前你在天平之外审视战场，可以自由观察对决！
          </span>
        </div>
      )}

      {/* CORE CONTROLLER STACK BASED ON GAME STATES */}
      <div className="w-full flex flex-col items-stretch mt-1">

        {/* State: Role selection start */}
        {phase === "ROLE_CHOICE" && (
          <div className="flex flex-col items-center gap-4">
            <span className="font-mono text-[10px] text-yellow-500 font-bold uppercase tracking-widest">
              — 在开始前决定你的底牌身份 —
            </span>
            <div className="flex items-center gap-4">
              <select
                value={chosenRole}
                onChange={(e) => setChosenRole(e.target.value as any)}
                className="bg-black border-4 border-black text-[#e0e0e0] px-4 py-2 text-xs font-sans font-bold select-none focus:outline-none focus:border-yellow-500"
              >
                <option value="预言家">预言家 (Seer)</option>
                <option value="女巫">女巫 (Witch)</option>
                <option value="猎人">猎人 (Hunter)</option>
                <option value="狼人">狼人 (Werewolf)</option>
                <option value="狼王">狼王 (Alpha Wolf)</option>
                <option value="白狼">白狼 (White Wolf)</option>
                <option value="狼美人">狼美人 (Wolf Beauty)</option>
                <option value="守卫狼">守卫狼 (Guardian Wolf)</option>
                <option value="隐狼">隐狼 (Hidden Wolf)</option>
                <option value="血月使徒">血月使徒 (Blood Moon Apostle)</option>
                <option value="梦魇狼">梦魇狼 (Nightmare Wolf)</option>
                <option value="守卫">守卫 (Guard)</option>
                <option value="白痴">白痴 (Idiot)</option>
                <option value="长老">长老 (Elder)</option>
                <option value="骑士">骑士 (Knight)</option>
                <option value="魔术师">魔术师 (Magician)</option>
                <option value="丘比特">丘比特 (Cupid)</option>
                <option value="乌鸦">乌鸦 (Raven)</option>
                <option value="守墓人">守墓人 (Graveyard Keeper)</option>
                <option value="盗贼">盗贼 (Thief)</option>
                <option value="村民">村民 (Villager)</option>
              </select>
              
              <TombstoneButton onClick={() => resetGame(chosenRole)}>
                <Flame className="w-4 h-4 text-red-600 animate-pulse" />
                入位对决 (Draw Card)
              </TombstoneButton>
            </div>
          </div>
        )}

        {/* State: NIGHT WEREWOLF ACTION */}
        {phase === "NIGHT_WOLF" && (
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 w-full px-2">
            {WOLF_CAMP.includes(user?.role || "") && !isDead ? (
              <div className="flex-grow flex items-center gap-3 w-full">
                <div className="relative flex-grow">
                  <input
                    type="text"
                    disabled
                    value=""
                    placeholder="狼人袭杀阶段：请点击右侧释放技能选取目标..."
                    className="w-full bg-transparent border border-zinc-900/80 text-[#e0e0e0] px-4 py-2 text-xs font-sans font-medium focus:outline-none rounded text-zinc-500 cursor-not-allowed"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-red-600 animate-pulse" />
                </div>
                
                <button
                  type="button"
                  onClick={() => setSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-600 border border-amber-500 text-black hover:bg-amber-500 transition-all font-sans font-bold uppercase tracking-widest shadow-[0_0_10px_rgba(245,158,11,0.5)] z-10 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <Flame className="w-3.5 h-3.5" />
                  释放技能
                </button>

                <button
                  type="button"
                  onClick={() => setIsSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1f1a2e]/60 border border-indigo-900/60 text-[10px] text-indigo-300 hover:bg-[#a5b4fc] transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  查看图鉴
                </button>
              </div>
            ) : (
              /* Dormant / AI werewolf is deciding */
              <div className="flex items-center justify-between w-full">
                <div className="text-zinc-550 font-sans text-xs italic">
                  🌒 夜深了... 狼人正在夜色中讨论并选择袭杀目标...
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsSkillModalOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-950/40 border border-indigo-900/50 text-[10px] text-indigo-300 hover:bg-indigo-900 hover:text-indigo-100 transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 cursor-pointer shrink-0"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    查看神职
                  </button>
                  <TombstoneButton onClick={() => nightSkillAction("NIGHT_KILL", 2)}>
                    跳过等待 (Skip Night)
                  </TombstoneButton>
                </div>
              </div>
            )}
          </div>
        )}

        {/* State: NIGHT SEER ACTION */}
        {phase === "NIGHT_SEER" && (
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 w-full px-2">
            {user?.role === "预言家" && !isDead ? (
              <div className="flex-grow flex items-center gap-3 w-full">
                <div className="relative flex-grow">
                  <input
                    type="text"
                    disabled
                    value=""
                    placeholder="预言家真视阶段：请点击右侧释放技能查验身份..."
                    className="w-full bg-transparent border border-zinc-900/80 text-[#e0e0e0] px-4 py-2 text-xs font-sans font-medium focus:outline-none rounded text-zinc-500 cursor-not-allowed"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-purple-600 animate-pulse" />
                </div>
                
                <button
                  type="button"
                  onClick={() => setSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-600 border border-amber-500 text-black hover:bg-amber-500 transition-all font-sans font-bold uppercase tracking-widest shadow-[0_0_10px_rgba(245,158,11,0.5)] z-10 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <Flame className="w-3.5 h-3.5" />
                  释放技能
                </button>

                <button
                  type="button"
                  onClick={() => setIsSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1f1a2e]/60 border border-indigo-900/60 text-[10px] text-indigo-300 hover:bg-[#a5b4fc] transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  查看图鉴
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between w-full">
                <div className="text-zinc-550 font-sans text-xs italic">
                  🌟 漫天繁星，预言家正在进行夜间查验，推算真实底牌...
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsSkillModalOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-950/40 border border-indigo-900/50 text-[10px] text-indigo-300 hover:bg-indigo-900 hover:text-indigo-100 transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 cursor-pointer shrink-0"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    查看神职
                  </button>
                  <TombstoneButton onClick={() => nightSkillAction("NIGHT_INSPECT", 4)}>
                    跳过查验 (Skip Inspect)
                  </TombstoneButton>
                </div>
              </div>
            )}
          </div>
        )}

        {/* State: NIGHT WITCH ACTION */}
        {phase === "NIGHT_WITCH" && (
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 w-full px-2">
            {user?.role === "女巫" && !isDead ? (
              <div className="flex-grow flex items-center gap-3 w-full">
                <div className="relative flex-grow">
                  <input
                    type="text"
                    disabled
                    value=""
                    placeholder={victimId ? `女巫秘药阶段：昨夜 ${victimId} 号倒牌，点击释放技能使用遗忘录/毒药...` : "女巫秘药阶段：昨夜平安，点击释放技能使用毒药..."}
                    className="w-full bg-transparent border border-zinc-900/80 text-[#e0e0e0] px-4 py-2 text-xs font-sans font-medium focus:outline-none rounded text-zinc-500 cursor-not-allowed"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                </div>
                
                {victimId && (
                  <button 
                    type="button" 
                    onClick={() => nightSkillAction("NIGHT_SAVED_OR_POISON", victimId, { saved: true, poisonTarget: null })} 
                    className="px-3 py-1.5 font-bold font-sans text-[10px] text-fuchsia-300 border border-fuchsia-900/50 bg-fuchsia-950/40 rounded uppercase tracking-widest hover:bg-fuchsia-900 transition-all shadow-md shrink-0 whitespace-nowrap active:scale-95"
                  >
                    解药援救
                  </button>
                )}
                
                <button
                  type="button"
                  onClick={() => setSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-600 border border-amber-500 text-black hover:bg-amber-500 transition-all font-sans font-bold uppercase tracking-widest shadow-[0_0_10px_rgba(245,158,11,0.5)] z-10 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <Flame className="w-3.5 h-3.5" />
                  释放技能
                </button>

                <button
                  type="button"
                  onClick={() => setIsSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1f1a2e]/60 border border-indigo-900/60 text-[10px] text-indigo-300 hover:bg-[#a5b4fc] transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  查看图鉴
                </button>
                
                {/* Dry Skip */}
                <button onClick={() => nightSkillAction("NIGHT_SAVED_OR_POISON", 0, { saved: false, poisonTarget: null })} className="px-4 py-2 font-mono text-[10px] text-zinc-400 border border-zinc-700 hover:bg-zinc-800 rounded shrink-0 transition-all font-bold tracking-widest">
                  跳过
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between w-full">
                <div className="text-zinc-550 font-sans text-xs italic">
                  ⚗ 实验台上，女巫正在将邪恶毒草与幽冥圣水在大釜里秘密搅拌调混...
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsSkillModalOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-950/40 border border-indigo-900/50 text-[10px] text-indigo-300 hover:bg-indigo-900 hover:text-indigo-100 transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 cursor-pointer shrink-0"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    查看神职
                  </button>
                  <TombstoneButton onClick={() => nightSkillAction("NIGHT_SAVED_OR_POISON", 0, { saved: false, poisonTarget: null })}>
                    跳过来药调配 (Skip Potions)
                  </TombstoneButton>
                </div>
              </div>
            )}
          </div>
        )}

        {/* State: DAY CASUALTY ANNOUNCEMENT */}
        {phase === "DAY_ANNOUNCEMENT" && (
          <div className="flex flex-col items-center gap-3">
            <span className="font-sans text-xs text-yellow-500 tracking-wider text-center">旭日已升，圆形议席的烛光熄灭。</span>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setIsSkillModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-950/40 border border-indigo-900/50 text-[10px] text-indigo-300 hover:bg-indigo-900 hover:text-indigo-100 transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 cursor-pointer"
              >
                <BookOpen className="w-3.5 h-3.5" />
                查看图鉴
              </button>
              <TombstoneButton onClick={transitionToDebate}>
                <Shield className="w-4.5 h-4.5 text-yellow-500 animate-pulse" />
                前往广场
              </TombstoneButton>
            </div>
          </div>
        )}

        {/* State: DAY SHERIFF ELECTION */}
        {phase === "DAY_SHERIFF_RUN" && (
          <div className="flex flex-col items-center gap-4 py-3 w-full max-w-[480px] mx-auto select-none">
            <div className="flex flex-col items-center text-center">
              <span className="font-serif text-lg text-amber-500 tracking-widest font-black uppercase drop-shadow-[0_0_8px_rgba(245,158,11,0.6)] flex items-center justify-center gap-2">
                <Crown className="w-5 h-5 flex-shrink-0" />
                警长竞选
                <Crown className="w-5 h-5 flex-shrink-0" />
              </span>
              <div className="w-32 h-px bg-gradient-to-r from-transparent via-amber-700/50 to-transparent mt-1.5 mb-1.5"></div>
              <span className="font-sans text-[10px] text-zinc-400 max-w-[300px] leading-relaxed">
                群居之巅，号令裁决之权。<br />当选者将戴上桂冠，享有 1.5 倍神圣归票权。<br />
                <span className="text-zinc-500 italic mt-1 block">您是否踏入此局？</span>
              </span>
            </div>

            <div className="flex items-stretch justify-center gap-5 mt-2 w-full px-2 relative">
              <button
                type="button"
                onClick={() => setIsSkillModalOpen(true)}
                title="查看技能"
                className="absolute left-[-20px] top-1/2 -translate-y-1/2 flex flex-col items-center justify-center gap-1 w-10 h-10 rounded-full bg-indigo-950/40 border border-indigo-900/50 hover:bg-indigo-900 hover:text-indigo-100 transition-all shadow-md z-10 active:scale-95 cursor-pointer text-indigo-300 hidden sm:flex"
              >
                <BookOpen className="w-4 h-4" />
              </button>

              {/* Card: Run */}
              <button
                onClick={() => useGameStore.getState().sheriffRunResolve(true)} disabled={isDead}
                className="relative flex-1 group overflow-hidden rounded border border-amber-900/60 bg-zinc-950/80 py-3 px-2 hover:border-amber-500/80 hover:bg-zinc-900 transition-all duration-500 disabled:opacity-50 disabled:cursor-not-allowed min-w-[120px] max-w-[150px] cursor-pointer shadow-lg"
              >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,_var(--tw-gradient-stops))] from-amber-700/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
                
                <div className="relative z-10 flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-full border border-amber-700/50 flex items-center justify-center bg-zinc-900/80 group-hover:bg-amber-950/60 transition-colors shadow-[0_0_15px_rgba(245,158,11,0.1)] group-hover:shadow-[0_0_20px_rgba(245,158,11,0.3)]">
                    <Shield className="w-4 h-4 text-amber-500 drop-shadow-md" />
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="font-serif text-sm font-black text-amber-100 tracking-widest drop-shadow mt-1">上警竞选</span>
                    <span className="font-serif text-[9px] text-amber-500/70 tracking-widest uppercase mt-0.5 scale-90 opacity-80">The Emperor</span>
                  </div>
                </div>
                {/* Decorative corners */}
                <div className="absolute top-1 left-1 w-2 h-2 border-t border-l border-amber-700/50 pointer-events-none"></div>
                <div className="absolute top-1 right-1 w-2 h-2 border-t border-r border-amber-700/50 pointer-events-none"></div>
                <div className="absolute bottom-1 left-1 w-2 h-2 border-b border-l border-amber-700/50 pointer-events-none"></div>
                <div className="absolute bottom-1 right-1 w-2 h-2 border-b border-r border-amber-700/50 pointer-events-none"></div>
              </button>

              {/* Card: Withdraw */}
              <button
                onClick={() => useGameStore.getState().sheriffRunResolve(false)} disabled={isDead}
                className="relative flex-1 group overflow-hidden rounded border border-zinc-800/80 bg-zinc-950/80 py-3 px-2 hover:border-zinc-500/80 hover:bg-zinc-900 transition-all duration-500 min-w-[120px] max-w-[150px] cursor-pointer shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,_var(--tw-gradient-stops))] from-zinc-700/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
                
                <div className="relative z-10 flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-full border border-zinc-700/50 flex items-center justify-center bg-zinc-900/80 group-hover:bg-zinc-800/60 transition-colors grayscale group-hover:grayscale-0">
                    <EyeOff className="w-4 h-4 text-zinc-400 group-hover:text-zinc-300 drop-shadow-md" />
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="font-serif text-sm font-black text-zinc-300 tracking-widest drop-shadow mt-1">退水旁观</span>
                    <span className="font-serif text-[9px] text-zinc-500 tracking-widest uppercase mt-0.5 scale-90 opacity-80">The Hermit</span>
                  </div>
                </div>
                {/* Decorative corners */}
                <div className="absolute top-1 left-1 w-2 h-2 border-t border-l border-zinc-700/40 pointer-events-none"></div>
                <div className="absolute top-1 right-1 w-2 h-2 border-t border-r border-zinc-700/40 pointer-events-none"></div>
                <div className="absolute bottom-1 left-1 w-2 h-2 border-b border-l border-zinc-700/40 pointer-events-none"></div>
                <div className="absolute bottom-1 right-1 w-2 h-2 border-b border-r border-zinc-700/40 pointer-events-none"></div>
              </button>
            </div>
          </div>
        )}

        {/* State: DAY SHERIFF VOTING */}
        {phase === "DAY_SHERIFF_VOTE" && (
          <div className="flex flex-col items-center gap-4 py-2 w-full max-w-[500px] mx-auto select-none">
            <div className="flex flex-col items-center text-center">
              <span className="font-serif text-lg text-amber-500 tracking-widest font-black uppercase drop-shadow-[0_0_8px_rgba(245,158,11,0.6)] flex items-center justify-center gap-2">
                <Crown className="w-5 h-5 flex-shrink-0" />
                警徽授受
                <Crown className="w-5 h-5 flex-shrink-0" />
              </span>
              <div className="w-32 h-px bg-gradient-to-r from-transparent via-amber-700/50 to-transparent mt-1.5 mb-2"></div>
              {!isDead ? (
                gameState.sheriffCandidates?.includes(user?.id || -1) ? (
                  <span className="font-sans text-[10px] text-zinc-400 mt-1 max-w-[300px] text-center italic">
                    您已踏入权力的角逐，退水的信徒正在为您与他们投下选票...
                  </span>
                ) : (
                  <span className="font-sans text-[10px] text-zinc-400 mt-1 max-w-[300px] text-center italic">
                    请在下方序列选取您支持的候选人，授其荣光。
                  </span>
                )
              ) : (
                <span className="font-sans text-[10px] text-zinc-500 mt-1 max-w-[300px] text-center italic">
                  您已长眠沉沦，命运交由生者裁决。
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 shrink-0">
              {!isDead ? (
                gameState.sheriffCandidates?.includes(user?.id || -1) ? (
                  <button
                    onClick={() => useGameStore.getState().castSheriffVote(null)}
                    className="relative px-6 py-2 bg-zinc-950 border border-zinc-800 rounded text-yellow-500/80 font-serif font-black tracking-widest uppercase hover:bg-zinc-900 transition-colors shadow-lg group overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,_var(--tw-gradient-stops))] from-yellow-700/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <span className="relative z-10 flex items-center gap-2 text-[11px]">
                      <Shield className="w-4 h-4 animate-pulse" />
                      等待裁决 (Skip)
                    </span>
                  </button>
                ) : (
                  <div className="bg-zinc-950/50 border border-zinc-800/80 rounded-md p-2">
                    <ActionTargetSelector 
                       actionName="授受荣光"
                       actionIcon="👑"
                       themeColor="yellow"
                       actionPrefix="公开授位"
                       actionPrompt=""
                       eligiblePlayers={gameState.players.filter(p => p.isAlive && gameState.sheriffCandidates?.includes(p.id))}
                       onConfirm={() => useGameStore.getState().castSheriffVote()}
                    />
                  </div>
                )
              ) : (
                  <button disabled className="px-6 py-2 bg-zinc-950/50 border border-zinc-800/50 rounded text-zinc-600 font-serif font-black tracking-widest uppercase cursor-not-allowed flex items-center gap-2 text-[11px]">
                    <Skull className="w-4 h-4" /> 幽灵旁观
                  </button>
              )}
            </div>
          </div>
        )}

        {/* State: DAY PLAYERS DEBATE (AI OR USER) */}
        {phase === "DAY_DEBATE" && (
          <div className="w-full flex flex-col md:flex-row items-center justify-between gap-4 px-2">
            
            {/* Speaking execution */}
            {gameState.currentSpeakerId === 1 ? (
              /* It is User speaking! Show input console and Parchment confirm button */
              <div className="flex-grow flex items-center gap-3 w-full">
                <div className="relative flex-grow">
                  <input
                    type="text"
                    value={userSpeechText}
                    onChange={(e) => setUserSpeechText(e.target.value)}
                    placeholder="轮到你的表述时间！请用犀利的逻辑反击狼人，争取好人信任..."
                    className="w-full bg-transparent border border-zinc-800/40 text-[#e0e0e0] px-4 py-2 text-xs font-sans font-medium focus:outline-none focus:border-red-650 rounded placeholder-zinc-500"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                </div>
                
                <button
                  type="button"
                  onClick={() => isDeadHunter ? setSkillModalOpen(true) : undefined}
                  disabled={!isDeadHunter}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 whitespace-nowrap shrink-0 ${
                    isDeadHunter 
                      ? "bg-amber-600 border border-amber-500 text-black hover:bg-amber-500 cursor-pointer shadow-[0_0_10px_rgba(245,158,11,0.5)]" 
                      : "bg-red-950/40 border border-red-900/50 text-[10px] text-red-300/50 cursor-not-allowed"
                  }`}
                  title={isDeadHunter ? "释放技能" : "非技能释放阶段"}
                >
                  <Flame className="w-3.5 h-3.5" />
                  释放技能
                </button>

                <button
                  type="button"
                  onClick={() => setIsSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1f1a2e]/60 border border-indigo-900/60 text-[10px] text-indigo-300 hover:bg-indigo-900 hover:text-[#fff] transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  查看图鉴
                </button>

                <ParchmentButton onClick={submitUserSpeech} disabled={!userSpeechText.trim()}>
                  <Send className="w-3.5 h-3.5" />
                  确认发言
                </ParchmentButton>
              </div>
            ) : (
              /* It's an AI speaking. Provide step triggers */
              <div className="flex items-center gap-3 shrink-0">
                <span className="font-sans text-[11px] text-zinc-400 font-bold mr-1">
                  正在请听：卡牌 {gameState.currentSpeakerId} 号的质询和推理。
                </span>
                
                <button
                  type="button"
                  onClick={() => isDeadHunter ? setSkillModalOpen(true) : undefined}
                  disabled={!isDeadHunter}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 whitespace-nowrap shrink-0 ${
                    isDeadHunter 
                      ? "bg-amber-600 border border-amber-500 text-black hover:bg-amber-500 cursor-pointer shadow-[0_0_10px_rgba(245,158,11,0.5)]" 
                      : "bg-red-950/40 border border-red-900/50 text-[10px] text-red-300/50 cursor-not-allowed"
                  }`}
                  title={isDeadHunter ? "释放技能" : "非技能释放阶段"}
                >
                  <Flame className="w-3.5 h-3.5" />
                  释放技能
                </button>

                <button
                  type="button"
                  onClick={() => setIsSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1f1a2e]/60 border border-indigo-900/60 text-[10px] text-indigo-300 hover:bg-[#a5b4fc] transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 whitespace-nowrap cursor-pointer shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  查看图鉴
                </button>

                <ParchmentButton onClick={simulateNextAI}>
                  <Play className="w-3.5 h-3.5" />
                  下一步发言
                </ParchmentButton>
              </div>
            )}
          </div>
        )}

        {/* State: DAY VOTING DECISION */}
        {phase === "DAY_VOTE" && (
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 w-full px-2">
            {!isDead ? (
              <>
                <div className="text-zinc-400 font-mono text-xs max-w-xl antialiased font-semibold">
                  🗳️ <span className="text-yellow-400 font-bold uppercase">[ 最后的审判 ]</span> 辩论大门已经紧闭。点击在座所有人生杀大权完全呈现，对可疑者投下流放印章！
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsSkillModalOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-950/40 border border-indigo-900/50 text-[10px] text-indigo-300 hover:bg-indigo-900 hover:text-indigo-100 transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 cursor-pointer"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    查看神职
                  </button>
                  <ActionTargetSelector 
                     actionName="流放投票"
                     actionIcon="🗳️"
                     themeColor="amber"
                     actionPrefix="法庭公投"
                     actionPrompt="请在下方序列选取您要流放的目标："
                     eligiblePlayers={gameState.players.filter(p => p.isAlive && !p.isUser)}
                     onConfirm={() => castVote()}
                  />
                </div>
              </>
            ) : (
              <div className="flex items-center justify-between w-full">
                <div className="text-zinc-550 font-sans text-xs italic">
                  🗳️ 村民正在圆形议事桌案前投出各自的石制印章，决选流放疑犯。宿命轮转中...
                </div>
                <button
                  type="button"
                  onClick={() => setIsSkillModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-950/40 border border-indigo-900/50 text-[10px] text-indigo-300 hover:bg-indigo-900 hover:text-indigo-100 transition-all font-sans font-bold uppercase tracking-widest shadow-md z-10 active:scale-95 cursor-pointer shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  查看神职
                </button>
              </div>
            )}
          </div>
        )}

        {/* State: GAME OVER AND RESTART */}
        {phase === "GAME_OVER" && (
          <div className="flex flex-col items-center gap-4">
            <span className="font-mono text-xs tracking-widest text-[#ef4444] font-extrabold uppercase animate-bounce ink-shadow text-center">
              ♛ 审判法阵归于平静。尘埃落定 ♛
            </span>
            <TombstoneButton onClick={() => resetGame("预言家")}>
              <RefreshCw className="w-4 h-4 text-emerald-400" />
              重开新一局审判
            </TombstoneButton>
          </div>
        )}

        <SkillReleaseModal 
          isOpen={skillModalOpen} 
          onClose={() => setSkillModalOpen(false)}
          actionName={skillConfig.actionName}
          actionIcon={skillConfig.icon}
          eligiblePlayers={gameState.players.filter(p => p.isAlive && !p.isUser)}
          onConfirm={skillConfig.confirm}
          userRole={user?.role || "村民"}
        />

      </div>
    </div>
  );
}

