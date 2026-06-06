import React from "react";
import { useGameStore } from "../store";
import { 
  Eye, 
  Sparkles, 
  ShieldAlert, 
  Flame, 
  Heart, 
  Skull, 
  Crosshair, 
  Zap, 
  Compass, 
  Moon 
} from "lucide-react";
import { motion } from "motion/react";

export default function SkillBar({ hideHeader = false }: { hideHeader?: boolean }) {
  const gameState = useGameStore((state) => state.state);
  const selectedCardId = useGameStore((state) => state.selectedCardId);
  const setSelectedCardId = useGameStore((state) => state.setSelectedCardId);
  const nightSkillAction = useGameStore((state) => state.nightSkillAction);
  const setTargetingSkill = useGameStore((state) => state.setTargetingSkill);

  if (!gameState) return null;

  const phase = gameState.phase;
  const user = gameState.players.find((p) => p.isUser);
  const isDead = user ? !user.isAlive : true;
  const userRole = user?.role || "村民";

  // Inner target dropdown helper for casting skills directly on selection
  const TargetDropdown = ({ 
    currentVal, 
    onChange, 
    filterFn 
  }: { 
    currentVal: number | null; 
    onChange: (id: number) => void; 
    filterFn: (p: any) => boolean;
  }) => {
    const targets = gameState.players.filter(filterFn);
    return (
      <div className="flex flex-col gap-1 w-full sm:w-auto min-w-[110px]" onClick={(e) => e.stopPropagation()}>
        <select
          value={currentVal || ""}
          onChange={(e) => {
            const val = Number(e.target.value);
            if (val) onChange(val);
          }}
          className="bg-black/90 border border-zinc-800 text-[10px] text-yellow-500 font-sans px-2 py-1 focus:border-yellow-500 rounded outline-none cursor-pointer"
        >
          <option value="" disabled>-- 选定施放目标 --</option>
          {targets.map((p) => (
            <option key={p.id} value={p.id} className="bg-zinc-950 text-zinc-300">
              {p.id}号席 - {p.name.replace(/\(.*?\)/g, "").trim()}
            </option>
          ))}
        </select>
      </div>
    );
  };

  // Quick action post handler for custom Hunter Shoot
  const executeHunterShoot = async (targetId: number) => {
    // Show Hunter gunshot visual overlay!
    const triggerCast = useGameStore.getState().triggerCast;
    const targetPlayer = gameState.players.find(p => p.id === targetId);
    if (triggerCast) {
      triggerCast({
        casterId: "USER",
        casterName: "你 (玩家 1 号 - 猎人)",
        role: "猎人",
        skillName: "猎人开枪",
        skillSub: "HUNTER GUNFIRE",
        targetId,
        targetName: targetPlayer ? targetPlayer.name : `玩家 ${targetId} 号`,
        effectType: "shoot"
      });
    }

    try {
      useGameStore.setState({ isLoading: true });
      await new Promise(resolve => setTimeout(resolve, 2400));
      const res = await fetch("/api/game/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "HUNTER_SHOOT", targetId })
      });
      const data = await res.json();
      useGameStore.setState({ state: data, selectedCardId: null, isLoading: false });
    } catch (err) {
      console.error("Failed to execute Hunter Shot:", err);
      useGameStore.setState({ isLoading: false });
    }
  };

  // Check if skills have been exhausted based on gameState
  const isSeerSkillUsed = gameState.seerVerifiedTarget !== null;
  const isWitchSaveUsed = gameState.witchSaved;
  const isWitchPoisonUsed = gameState.witchPoisonedTarget !== null;
  const isWolfBiteUsed = gameState.wolfKilledTarget !== null;

  // Render a specific skill card
  const SkillCard = ({
    title,
    subtitle,
    description,
    type, // "active" | "passive" | "reactive"
    status, // "ready" | "locked" | "exhausted" | "passive"
    icon: IconComp,
    glowColor,
    actionButton,
  }: {
    title: string;
    subtitle: string;
    description: string;
    type: "主动" | "被动" | "限时";
    status: "就绪" | "锁定" | "用尽" | "恒驻";
    icon: React.ComponentType<any>;
    glowColor: string; // e.g., "border-yellow-500 shadow-yellow-500/20"
    actionButton?: React.ReactNode;
  }) => {
    // Styling based on status
    const getStatusStyle = () => {
      switch (status) {
        case "就绪":
          return "bg-emerald-950/40 border-emerald-500/60 text-emerald-400";
        case "锁定":
          return "bg-zinc-950/80 border-zinc-900 text-zinc-500";
        case "用尽":
          return "bg-red-950/20 border-red-950 text-red-500/60";
        case "恒驻":
          return "bg-indigo-950/40 border-indigo-500/60 text-indigo-400";
        default:
          return "bg-zinc-950 border-zinc-900 text-zinc-400";
      }
    };

    const statusStyle = getStatusStyle();

    return (
      <div 
        className={`relative flex flex-col md:flex-row items-start md:items-center justify-between p-3.5 border-2 rounded min-w-[280px] max-w-sm flex-1 transition-all duration-300 ${
          status === "就绪" ? `shadow-[0_0_12px_rgba(0,0,0,0.5)] border-l-4 hover:scale-[1.02]` : ""
        } ${status === "锁定" ? "opacity-60" : ""} bg-gradient-to-r from-black/50 to-zinc-950/30 backdrop-blur-sm`}
        style={{
          borderColor: status === "就绪" ? undefined : (status === "恒驻" ? "#4f46e5" : undefined),
        }}
        id={`skill-${title.replace(/\s+/g, "-")}`}
      >
        {/* Status Accent Beam */}
        {status === "就绪" && (
          <div 
            className="absolute left-0 top-0 bottom-0 w-1" 
            style={{ backgroundColor: glowColor.includes("yellow") ? "#eab308" : (glowColor.includes("fuchsia") ? "#d946ef" : "#10b981") }}
          />
        )}

        <div className="flex gap-3 items-start select-none">
          <div className={`p-2 rounded bg-black/60 border border-zinc-800 ${status === "就绪" ? "animate-pulse" : ""}`}>
            <IconComp className="w-5 h-5" style={{ color: status === "就绪" ? (glowColor.includes("yellow") ? "#eab308" : (glowColor.includes("fuchsia") ? "#d946ef" : "#10b981")) : undefined }} />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-serif text-xs font-black text-[#f5f5f5] tracking-wide">{title}</span>
              <span className={`text-[8.5px] px-1.5 py-0.5 rounded-full font-mono font-extrabold uppercase tracking-widest border ${statusStyle}`}>
                {status}
              </span>
            </div>
            <span className="text-[9px] text-zinc-500 font-mono mt-0.5">{subtitle} ∙ <span className="text-zinc-600 font-sans">{type}技能</span></span>
            <span className="text-[10px] text-zinc-400 font-sans leading-relaxed mt-1.5 max-w-[220px]">{description}</span>
          </div>
        </div>

        {/* Action Button Segment */}
        {status === "就绪" && actionButton && (
          <div className="mt-3 md:mt-0 ml-0 md:ml-4 w-full md:w-auto shrink-0 flex justify-end">
            {actionButton}
          </div>
        )}
      </div>
    );
  };
  const renderSkills = () => {
    switch (userRole) {
      case "预言家":
        return (
          <>
            {/* Skill 1: Divine Divination */}
            <SkillCard
              title="预言查验"
              subtitle="SEER INSPECT"
              description="🔮 夜幕时刻，窥探星辰轨迹。开启此技能后可弹窗选择一名场上存活的玩家，直接窥视并查验其底牌属于恶狼还是好人。"
              type="主动"
              status={
                phase !== "NIGHT_SEER" 
                  ? "锁定" 
                  : (isSeerSkillUsed ? "用尽" : "就绪")
              }
              icon={Eye}
              glowColor="shadow-yellow-500/20"
              actionButton={
                <button
                  onClick={() => setTargetingSkill({
                    type: "NIGHT_INSPECT",
                    title: "🔮 圣贤预言 ∙ 照亮夜裔",
                    subtitle: "SEER DIVINATION EYE",
                    description: "神庭命盘开始转动，请在下方点击挑选一名在阵的玩家查明其是恶狼（狼人）还是凡骨（好人）。"
                  })}
                  disabled={phase !== "NIGHT_SEER" || isSeerSkillUsed}
                  className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-40 disabled:cursor-not-allowed border-2 border-yellow-800 rounded font-sans font-black text-[9.5px] text-[#000] uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                >
                  开启查验神眼
                </button>
              }
            />

            {/* Skill 2: Cosmic Intuition */}
            <SkillCard
              title="查验备忘"
              subtitle="SEER MEMO"
              description="查验过的目标身份会同步记录在卡牌旁的私密札记上，辅助信息 analysis 与推理引导。"
              type="被动"
              status="恒驻"
              icon={Sparkles}
              glowColor="shadow-indigo-500/10"
            />
          </>
        );

      case "女巫":
        return (
          <>
            {/* Skill 1: Healing Dew */}
            <SkillCard
              title="女巫解药"
              subtitle="WITCH ANTIDOTE"
              description={
                gameState.victimId !== null 
                  ? `🧪 昨晚遇难的玩家为 [ ${gameState.victimId} 号 ]，可施予圣水将其从死亡边缘救活。` 
                  : "今夜暂无死者，或者解药已被消耗。"
              }
              type="主动"
              status={
                phase !== "NIGHT_WITCH" 
                  ? "锁定" 
                  : (isWitchSaveUsed ? "用尽" : (gameState.victimId !== null ? "就绪" : "锁定"))
              }
              icon={Heart}
              glowColor="shadow-fuchsia-500/20"
              actionButton={
                <button
                  onClick={() => setTargetingSkill({
                    type: "NIGHT_HEAL",
                    title: "🧪 枯木逢春 ∙ 苏生圣水",
                    subtitle: "WITCH LIFE ELIXIR",
                    description: `昨晚落难的无辜凡人 (玩家 ${gameState.victimId} 号) 已被选定。倾注解药圣水可以净化利爪邪毒，逆转死生劫持。`
                  })}
                  disabled={phase !== "NIGHT_WITCH" || isWitchSaveUsed || gameState.victimId === null}
                  className="px-4 py-2 bg-fuchsia-600 hover:bg-fuchsia-500 disabled:opacity-40 border-2 border-fuchsia-800 rounded font-sans font-black text-[9.5px] text-white uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                >
                  使用苏生解药
                </button>
              }
            />

            {/* Skill 2: Deadly Poison */}
            <SkillCard
              title="女巫毒药"
              subtitle="WITCH POISON"
              description="💀 在邪恶黑夜里调配强酸毒药。开启后弹窗选择一名场上怀疑对象，直接投掷毒汁，待黎明时分将其抹杀出局。"
              type="主动"
              status={
                phase !== "NIGHT_WITCH" 
                  ? "锁定" 
                  : (isWitchPoisonUsed ? "用尽" : "就绪")
              }
              icon={Skull}
              glowColor="shadow-emerald-500/20"
              actionButton={
                <button
                  onClick={() => setTargetingSkill({
                    type: "NIGHT_POISON",
                    title: "💀 万古枯尽 ∙ 天谴之毒",
                    subtitle: "WITCH DEATH POTION",
                    description: "选定一名场上的眼中钉。此毒一出，断绝一切护体神力与流转因果，今夜过后彻底淘汰。"
                  })}
                  disabled={phase !== "NIGHT_WITCH" || isWitchPoisonUsed}
                  className="px-4 py-2 bg-emerald-650 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed border-2 border-emerald-800 rounded font-sans font-black text-[9.5px] text-[#000] uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                >
                  投下致命剧毒
                </button>
              }
            />
          </>
        );

      case "狼人":
        return (
          <>
            {/* Skill 1: Lycan Bite */}
            <SkillCard
              title="狼人袭击"
              subtitle="WEREWOLF ATTACK"
              description="🐺 邪月当空。狼人在夜幕下相互低语低吟。点击后会弹窗选择场上一名怀疑者神职人员，进行狂暴啃食袭击。"
              type="主动"
              status={
                phase !== "NIGHT_WOLF" 
                  ? "锁定" 
                  : (isWolfBiteUsed ? "用尽" : "就绪")
              }
              icon={Flame}
              glowColor="shadow-red-500/20"
              actionButton={
                <button
                  onClick={() => setTargetingSkill({
                    type: "NIGHT_KILL",
                    title: "🐺 血月降临 ∙ 狂暴爪袭击",
                    subtitle: "WEREWOLF RAIDING CLAW",
                    description: "群狼自幽暗密林深处探出利爪。选定一席将其猎杀淘汰，粉碎凡尘议会的气运。此操作将触发夜里撕咬特效。"
                  })}
                  disabled={phase !== "NIGHT_WOLF" || isWolfBiteUsed}
                  className="px-4 py-2 bg-red-650 hover:bg-red-600 disabled:opacity-40 border-2 border-red-900 rounded font-sans font-black text-[9.5px] text-[#f5f5f5] uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                >
                  集结狂嚎袭击
                </button>
              }
            />

            {/* Skill 2: Bloodlust Instinct */}
            <SkillCard
              title="狼人低语"
              subtitle="WEREWOLF WHISPERS"
              description="同伴间可以在夜色下共享并传达手势，集结袭击票数达成共识，刺杀好人目标。"
              type="被动"
              status="恒驻"
              icon={Moon}
              glowColor="shadow-red-500/10"
            />
          </>
        );

      case "猎人":
        // Hunter reactive logic: triggers when dead (voted out)
        const isUserDead = user ? !user.isAlive : true;
        
        return (
          <>
            {/* Skill 1: Vengeful Silver Bullet */}
            <SkillCard
              title="猎人开枪"
              subtitle="HUNTER RETALIATION"
              description={
                !isUserDead
                  ? "🔫 当你在白天表决投票中被流放或在夜间被吞食时，可在出局瞬间开枪带走场上一名玩家作为陪葬。"
                  : "☠️ 你的肉体已被撕咬或放逐。猎枪子弹在枪膛里怒嚎！点击右侧按钮锁定那名谋害者，扣下扳机一同拉入深渊！"
              }
              type="主动"
              status={isUserDead ? "就绪" : "锁定"}
              icon={Crosshair}
              glowColor="shadow-yellow-500/20"
              actionButton={
                <button
                  onClick={() => setTargetingSkill({
                    type: "HUNTER_SHOOT",
                    title: "🎯 临终反扑 ∙ 猎枪银弹",
                    subtitle: "HUNTER RETALIATION ROUND",
                    description: "胸口被撕咬/放逐。扳机已扣死！选定场上一名死敌，用最后一发驱邪银弹将其一同流放！"
                  })}
                  disabled={!isUserDead}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-40 border-2 border-red-800 rounded font-sans font-black text-[9.5px] text-white uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                >
                  扣下复仇扳机
                </button>
              }
            />

            {/* Skill 2: Steel Will */}
            <SkillCard
              title="开枪威慑"
              subtitle="HUNTER DETERRENCE"
              description="若被狼人夜袭啃食，你仍可鸣枪。但若被女巫使用毒药淘汰，则因药性禁闭无法发枪带人。"
              type="被动"
              status="恒驻"
              icon={ShieldAlert}
              glowColor="shadow-slate-500/10"
            />
          </>
        );

      default:
        return (
          <div className="text-zinc-500 font-mono text-[10px] uppercase tracking-wider italic text-center p-4">
            — 圣洁村民 (Plain Villager) 卡牌阵营，无专属主动神迹，请专注于严谨讨论和推理流放恶狼 —
          </div>
        );
    }
  };

  return (
    <div className="w-full flex flex-col gap-2 p-1 relative" id="skill-dock-container">
      {/* Decorative Title Border with Neon Underglow */}
      {!hideHeader && (
        <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2 mb-1 select-none">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-500 animate-pulse" />
            <span className="font-mono text-[10.5px] font-black tracking-widest text-zinc-350 uppercase">
              🔮 圣职命象卡牌专属技能契约 (Divine Spellbook & Spells)
            </span>
          </div>
          <div className="font-mono text-[8px] text-zinc-500 uppercase tracking-tighter">
            角色: <span className="text-yellow-500 font-extrabold">{userRole}</span>
          </div>
        </div>
      )}

      {/* Grid wrapper for skills */}
      <div className="flex flex-col sm:flex-row flex-wrap gap-4 items-stretch">
        {renderSkills()}
      </div>
    </div>
  );
}
