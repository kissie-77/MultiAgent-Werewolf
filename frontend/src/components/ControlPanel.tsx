import React, { useState } from "react";
import { useGameStore } from "../store";
import { Send, Play, RefreshCw, Skull, Shield, Eye, Flame, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import { motion } from "motion/react";
import SkillBar from "./SkillBar";

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

  const [chosenRole, setChosenRole] = useState<"预言家" | "女巫" | "猎人" | "狼人">("预言家");
  const [isSkillsExpanded, setIsSkillsExpanded] = useState(true);

  if (!gameState) return null;

  const phase = gameState.phase;
  const user = gameState.players.find((p) => p.isUser);
  const isDead = user ? !user.isAlive : true;
  const victimId = gameState.victimId;

  // Render Stone Tombstone-style Button (石碑风格按钮)
  const TombstoneButton = ({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) => (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`stone-btn relative px-6 py-3 font-sans font-black text-[#f5f5f5] uppercase tracking-widest transition-all duration-300 rounded shadow-lg flex items-center gap-2 ${
        disabled
          ? "opacity-45 cursor-not-allowed select-none saturate-50"
          : "hover:scale-105 active:translate-y-1"
      }`}
      style={{
        clipPath: "polygon(5% 0%, 95% 0%, 100% 15%, 100% 100%, 0% 100%, 0% 15%)",
      }}
    >
      <div className="absolute inset-x-0 top-0 h-1 bg-zinc-500/30" />
      {/* Tiny cracks effect */}
      <span className="absolute top-1 left-2 text-[8px] text-zinc-400 select-none">🕀</span>
      <span className="absolute bottom-1 right-2 text-[8px] text-zinc-400 select-none">✝</span>
      {children}
    </button>
  );

  // Render Parchment Scroll Button (羊皮纸风格按钮)
  const ParchmentButton = ({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) => (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`relative px-5 py-3 font-mono font-bold text-zinc-950 bg-amber-100/90 border-2 border-amber-900 transition-all duration-300 rounded shadow-[5px_5px_0px_#451a03] flex items-center gap-1.5 ${
        disabled
          ? "opacity-50 cursor-not-allowed bg-zinc-800 text-zinc-600 border-zinc-950"
          : "hover:bg-amber-50 hover:shadow-[2px_2px_0px_#451a03] hover:translate-x-0.5 hover:translate-y-0.5 active:translate-y-1"
      }`}
      style={{
        borderRadius: "4px 12px 4px 12px"
      }}
    >
      {/* Parchment scroll marks */}
      <div className="absolute -left-1 top-1/2 -translate-y-1/2 w-1.5 h-6 bg-amber-900 rounded-sm" />
      <div className="absolute -right-1 top-1/2 -translate-y-1/2 w-1.5 h-6 bg-amber-900 rounded-sm" />
      {children}
    </button>
  );

  // Render Wax Seal Stamp Button (封印印章风格)
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

  // Render Potion Bottle Button (药剂瓶风格)
  const PotionButton = ({ onClick, type, children, disabled }: { onClick: () => void; type: "elixir" | "poison"; children: React.ReactNode; disabled?: boolean }) => {
    // Poison is glowing green/fluorescent yellow, elixir is glowing neon violet/pink
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
    <div className="bg-transparent border-t border-zinc-900/35 px-6 py-4 flex flex-col gap-4 relative z-10 shrink-0 select-none min-h-[140px] justify-center">
      
      {/* Night and dead actions notification banner */}
      {isDead && phase !== "GAME_OVER" && (
        <div className="p-3 bg-red-950/15 border border-red-500/35 rounded text-center my-1 leading-relaxed">
          <span className="font-serif text-lg text-red-500 mr-2">☠</span>
          <span className="font-mono text-[#e0e0e0] text-xs font-black uppercase tracking-widest">
            你被放逐/吞噬，灵魂已归尘土。目前你在天平之外审视战场，可以自由观察对决！
          </span>
        </div>
      )}

      {/* Dynamic Interactive Skill & Spell deck Bar */}
      {phase !== "ROLE_CHOICE" && (
        <div className="w-full bg-transparent border border-zinc-900/40 rounded mb-2 overflow-hidden transition-all duration-300">
          {/* Header Toggle Toggle Bar */}
          <button 
            type="button"
            onClick={() => setIsSkillsExpanded(!isSkillsExpanded)}
            className="w-full px-4 py-2 flex items-center justify-between bg-transparent hover:bg-white/5 transition-all border-b border-zinc-900/40 text-left cursor-pointer select-none"
          >
            <div className="flex items-center gap-2">
              <span className="text-yellow-500 font-extrabold text-[11px] font-mono tracking-widest uppercase flex items-center gap-2">
                <span className="animate-pulse">🔮</span> 专属命象卡牌技能契约 (Divine Spellbook & Spells)
              </span>
              <span className="text-[9.5px] px-2 py-0.5 rounded-full border border-zinc-800 bg-zinc-950 text-yellow-500/95 font-black tracking-wider">
                {gameState.players.find(p => p.isUser)?.role || "村民"}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-zinc-400 hover:text-white font-mono font-bold transition-colors">
              <span>{isSkillsExpanded ? "收起面板" : "展开技能书"}</span>
              <span className="inline-block transition-transform duration-300" style={{ transform: isSkillsExpanded ? "rotate(180deg)" : "rotate(0deg)" }}>
                ▼
              </span>
            </div>
          </button>
          
          <motion.div
            initial={false}
            animate={{ 
              height: isSkillsExpanded ? "auto" : 0, 
              opacity: isSkillsExpanded ? 1 : 0 
            }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="overflow-hidden"
          >
            <div className="p-3">
              <SkillBar hideHeader />
            </div>
          </motion.div>
        </div>
      )}

      {/* CORE CONTROLLER STACK BASED ON GAME STATES */}
      <div className="flex flex-wrap items-center justify-center gap-6">

        {/* State: Role selection start */}
        {phase === "ROLE_CHOICE" && (
          <div className="flex flex-col items-center gap-4">
            <span className="font-mono text-[10px] text-yellow-500 font-bold uppercase tracking-widest">
              — 在开始审判前 决定你的宿命卡牌职业 —
            </span>
            <div className="flex items-center gap-4">
              <select
                value={chosenRole}
                onChange={(e) => setChosenRole(e.target.value as any)}
                className="bg-black border-4 border-black text-[#e0e0e0] px-4 py-2 text-xs font-sans font-bold select-none focus:outline-none focus:border-yellow-500"
              >
                <option value="预言家">预言神官 (Seer Apprentice)</option>
                <option value="女巫">猩红女巫 (Night Witch)</option>
                <option value="猎人">钢枪猎人 (Gunslinging Hunter)</option>
                <option value="狼人">荒野巨狼 (Werewolf Beast)</option>
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
          <div className="flex items-center gap-6">
            {user?.role === "狼人" && !isDead ? (
              <>
                <div className="text-zinc-400 font-mono text-xs font-medium max-w-sm">
                  📢 <span className="text-red-500 font-bold uppercase">[ 狼牙出鞘 ]</span> 你是凶残的狼人！请在左侧列表中点击选择你要撕咬啃食的目标，按下印章封死他！
                </div>
                <SealButton
                  disabled={selectedCardId === null}
                  onClick={() => selectedCardId && nightSkillAction("NIGHT_KILL", selectedCardId)}
                >
                  獠牙处决
                </SealButton>
              </>
            ) : (
              /* Dormant / AI werewolf is deciding */
              <div className="flex items-center gap-4">
                <div className="text-zinc-500 font-sans text-xs italic">
                  🌒 夜深了... 月隐迷雾，群兽在荒野嘶吼，狼人正在圆形厅柱阴影里低声抉择...
                </div>
                <TombstoneButton onClick={() => nightSkillAction("NIGHT_KILL", 2)}>
                  跳过黑夜等待 (Skip Night)
                </TombstoneButton>
              </div>
            )}
          </div>
        )}

        {/* State: NIGHT SEER ACTION */}
        {phase === "NIGHT_SEER" && (
          <div className="flex items-center gap-6">
            {user?.role === "预言家" && !isDead ? (
              <>
                <div className="text-zinc-400 font-mono text-xs font-medium max-w-sm">
                  🔮 <span className="text-yellow-500 font-bold uppercase">[ 烛照本真 ]</span> 你是法力强大的真预言家。请在卡卡牌列表中触碰可疑目标，点击石碑开启照妖镜！
                </div>
                <TombstoneButton
                  disabled={selectedCardId === null}
                  onClick={() => selectedCardId && nightSkillAction("NIGHT_INSPECT", selectedCardId)}
                >
                  <Eye className="w-4 h-4 text-[#eab308]" />
                  窥其宿命 (Inspect Alignment)
                </TombstoneButton>
              </>
            ) : (
              <div className="flex items-center gap-4">
                <div className="text-zinc-500 font-sans text-xs italic">
                  🌟 漫天幽星，预言神官正在擦拭明镜，推算星轨底牌...
                </div>
                <TombstoneButton onClick={() => nightSkillAction("NIGHT_INSPECT", 4)}>
                  跳过星盘查验 (Skip Inspect)
                </TombstoneButton>
              </div>
            )}
          </div>
        )}

        {/* State: NIGHT WITCH ACTION */}
        {phase === "NIGHT_WITCH" && (
          <div className="flex items-center gap-8">
            {user?.role === "女巫" && !isDead ? (
              <>
                <div className="text-zinc-400 font-mono text-xs max-w-md">
                  🧪 <span className="text-green-400 font-bold uppercase">[ 毒药与圣水 ]</span> 你是掌控生死的女巫。
                  昨晚被杀害的是 {victimId !== null ? `玩家 ${victimId} 号` : "无"}。你是否救人或赐人死亡？
                </div>
                
                {/* Healing potion (If casualty exists) */}
                <PotionButton
                  type="elixir"
                  disabled={victimId === null}
                  onClick={() => nightSkillAction("NIGHT_SAVED_OR_POISON", victimId || 0, { saved: true, poisonTarget: null })}
                >
                  圣水复苏
                </PotionButton>

                {/* Poison potion bottle */}
                <PotionButton
                  type="poison"
                  disabled={selectedCardId === null}
                  onClick={() => selectedCardId && nightSkillAction("NIGHT_SAVED_OR_POISON", selectedCardId, { saved: false, poisonTarget: selectedCardId })}
                >
                  见血封喉
                </PotionButton>

                {/* Dry Skip */}
                <TombstoneButton onClick={() => nightSkillAction("NIGHT_SAVED_OR_POISON", 0, { saved: false, poisonTarget: null })}>
                  静观其变 (Skip)
                </TombstoneButton>
              </>
            ) : (
              <div className="flex items-center gap-4">
                <div className="text-zinc-500 font-sans text-xs italic">
                  ⚗ 实验台上，女巫正在将邪恶毒草与幽冥圣水在大釜里秘密搅拌调混...
                </div>
                <TombstoneButton onClick={() => nightSkillAction("NIGHT_SAVED_OR_POISON", 0, { saved: false, poisonTarget: null })}>
                  跳过来药调配 (Skip Potions)
                </TombstoneButton>
              </div>
            )}
          </div>
        )}

        {/* State: DAY CASUALTY ANNOUNCEMENT */}
        {phase === "DAY_ANNOUNCEMENT" && (
          <div className="flex flex-col items-center gap-3">
            <span className="font-mono text-xs text-yellow-500 tracking-wider uppercase font-black">旭日已升，圆形议席的烛光熄灭。</span>
            <TombstoneButton onClick={transitionToDebate}>
              <Shield className="w-4.5 h-4.5 text-yellow-500 animate-pulse" />
              进入白昼大辩论 (Enter Debate Arena)
            </TombstoneButton>
          </div>
        )}

        {/* State: DAY PLAYERS DEBATE (AI OR USER) */}
        {phase === "DAY_DEBATE" && (
          <div className="w-full flex flex-col md:flex-row items-center justify-between gap-4">
            
            {/* Auto Play simulator switch on left */}
            <div className="flex items-center gap-3 bg-zinc-950/30 px-4 py-2 rounded border border-zinc-900/50 shadow-[1px_1px_4px_rgba(0,0,0,0.5)]">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isAutoPlaying}
                  onChange={toggleAutoPlay}
                  className="w-4 h-4 accent-red-600"
                />
                <span className="font-mono text-xs text-zinc-300 font-bold tracking-wider uppercase">
                  🎬 AI 自动轮流演讲 (Auto Debate)
                </span>
              </label>
              <span className={`w-2 h-2 rounded-full ${isAutoPlaying ? "bg-emerald-500 animate-ping" : "bg-zinc-700"}`} />
            </div>

            {/* Speaking execution */}
            {gameState.currentSpeakerId === 1 ? (
              /* It is User speaking! Show input console and Parchment confirm button */
              <div className="flex-grow flex items-center gap-3 max-w-2xl w-full">
                <div className="relative flex-grow">
                  <input
                    type="text"
                    value={userSpeechText}
                    onChange={(e) => setUserSpeechText(e.target.value)}
                    placeholder="轮到你的表述时间！请用犀利的逻辑反击狼人，争取好人信任..."
                    className="w-full bg-zinc-950/30 border border-zinc-900/60 text-[#e0e0e0] px-4 py-2.5 text-xs font-sans font-medium focus:outline-none focus:border-red-650 rounded placeholder-zinc-550"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                </div>
                
                <ParchmentButton onClick={submitUserSpeech} disabled={!userSpeechText.trim()}>
                  <Send className="w-3.5 h-3.5" />
                  确认发言
                </ParchmentButton>
              </div>
            ) : (
              /* It's an AI speaking. Provide step triggers */
              <div className="flex items-center gap-4">
                <span className="font-sans text-[11px] text-zinc-400 font-bold mr-1">
                  正在请听：卡牌 {gameState.currentSpeakerId} 号的质询和推理。
                </span>
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
          <div className="flex items-center gap-6">
            {!isDead ? (
              <>
                <div className="text-zinc-400 font-mono text-xs max-w-md antialiased font-semibold">
                  🗳️ <span className="text-yellow-400 font-bold uppercase">[ 最后的审判 ]</span> 辩论大门闭合！请在左侧触碰你最怀疑的恶狼卡牌，按下底部的红色印章印记，施放神圣处的制裁！
                </div>
                <SealButton
                  disabled={selectedCardId === null}
                  onClick={castVote}
                >
                  封印流放
                </SealButton>
              </>
            ) : (
              <div className="text-zinc-500 font-sans text-xs italic">
                🗳️ 村民正在圆形议事桌案前投出各自的石制印章，决选流放疑犯。宿命轮转中...
              </div>
            )}
          </div>
        )}

        {/* State: GAME OVER AND RESTART */}
        {phase === "GAME_OVER" && (
          <div className="flex flex-col items-center gap-4">
            <span className="font-mono text-xs tracking-widest text-[#ef4444] font-extrabold uppercase animate-bounce ink-shadow">
              ♛ 审判法阵归于平静。尘埃落定 ♛
            </span>
            <TombstoneButton onClick={() => resetGame("预言家")}>
              <RefreshCw className="w-4 h-4 text-emerald-400" />
              重开新一局审判
            </TombstoneButton>
          </div>
        )}

      </div>
    </div>
  );
}
