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
    try {
      useGameStore.setState({ isLoading: true });
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

  // Retrieve user skill components based on active role
  const renderSkills = () => {
    switch (userRole) {
      case "预言家":
        return (
          <>
            {/* Skill 1: Divine Divination */}
            <SkillCard
              title="天眼之瞳 ∙ 宿命查验"
              subtitle="DIVINE INSPECT"
              description={
                selectedCardId === null 
                  ? "🔍 请在桌上或左侧点选一名需要查验卡牌的席位..." 
                  : `🔮 已锁定 [玩家 ${selectedCardId} 号]！点击右侧按钮启动法阵查验。`
              }
              type="主动"
              status={
                phase !== "NIGHT_SEER" 
                  ? "锁定" 
                  : (isSeerSkillUsed ? "用尽" : "就绪")
              }
              icon={Eye}
              glowColor="shadow-yellow-500/20"
              actionButton={
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <TargetDropdown
                    currentVal={selectedCardId}
                    onChange={(id) => setSelectedCardId(id)}
                    filterFn={(p) => p.isAlive && !p.isUser}
                  />
                  <button
                    onClick={() => selectedCardId && nightSkillAction("NIGHT_INSPECT", selectedCardId)}
                    disabled={selectedCardId === null}
                    className="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-40 disabled:cursor-not-allowed border-2 border-yellow-800 rounded font-sans font-black text-[9px] text-[#000] uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                  >
                    窥探宿命
                  </button>
                </div>
              }
            />

            {/* Skill 2: Cosmic Intuition */}
            <SkillCard
              title="星轨预示 ∙ 烛光本源"
              subtitle="ASTRAL INTUITION"
              description="查验过的目标状态会同步追加于卡牌的私密札记上。知悉恶狼分布，并引导好人赢取胜局。"
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
              title="生机回转 ∙ 极光圣水"
              subtitle="HEALING ELIXIR"
              description={
                gameState.victimId !== null 
                  ? `🧪 锁定了昨晚遇难的 [玩家 ${gameState.victimId} 号]，可驱散死神魔咒拯救生命！` 
                  : "今晚暂无死者，或已消耗复活药水保护。"
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
                  onClick={() => nightSkillAction("NIGHT_SAVED_OR_POISON", gameState.victimId || 0, { saved: true, poisonTarget: null })}
                  className="px-3 py-1.5 bg-fuchsia-600 hover:bg-fuchsia-500 border-2 border-fuchsia-800 rounded font-sans font-black text-[9px] text-white uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                >
                  圣水复苏
                </button>
              }
            />

            {/* Skill 2: Deadly Poison */}
            <SkillCard
              title="荒芜枯萎 ∙ 见血封喉"
              subtitle="BLACK COLD POISON"
              description={
                selectedCardId === null 
                  ? "🧪 请选定一名你怀疑的卡牌席位，一滴极毒便可将其抹除..." 
                  : `💀 瓶中剧毒已瞄准 [玩家 ${selectedCardId} 号]！点击施放赐予死寂。`
              }
              type="主动"
              status={
                phase !== "NIGHT_WITCH" 
                  ? "锁定" 
                  : (isWitchPoisonUsed ? "用尽" : "就绪")
              }
              icon={Skull}
              glowColor="shadow-emerald-500/20"
              actionButton={
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <TargetDropdown
                    currentVal={selectedCardId}
                    onChange={(id) => setSelectedCardId(id)}
                    filterFn={(p) => p.isAlive && !p.isUser}
                  />
                  <button
                    onClick={() => selectedCardId && nightSkillAction("NIGHT_SAVED_OR_POISON", selectedCardId, { saved: false, poisonTarget: selectedCardId })}
                    disabled={selectedCardId === null}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed border-2 border-emerald-800 rounded font-sans font-black text-[9px] text-[#000] uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                  >
                    见血封喉
                  </button>
                </div>
              }
            />
          </>
        );

      case "狼人":
        return (
          <>
            {/* Skill 1: Lycan Bite */}
            <SkillCard
              title="暮色森罗 ∙ 獠牙狂噬"
              subtitle="LYCAN INTENSE BITE"
              description={
                selectedCardId === null 
                  ? "🐺 嗜血本能觉醒。请在桌上指定今晚要啃食的目标席位..." 
                  : `🩸 狼爪已抵住 [玩家 ${selectedCardId} 号] 的咽喉！执行吞噬猎杀。`
              }
              type="主动"
              status={
                phase !== "NIGHT_WOLF" 
                  ? "锁定" 
                  : (isWolfBiteUsed ? "用尽" : "就绪")
              }
              icon={Flame}
              glowColor="shadow-red-500/20"
              actionButton={
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <TargetDropdown
                    currentVal={selectedCardId}
                    onChange={(id) => setSelectedCardId(id)}
                    filterFn={(p) => p.isAlive && !p.isUser}
                  />
                  <button
                    onClick={() => selectedCardId && nightSkillAction("NIGHT_KILL", selectedCardId)}
                    disabled={selectedCardId === null}
                    className="px-3 py-1.5 bg-red-650 hover:bg-red-600 border-2 border-red-900 rounded font-sans font-black text-[9px] text-[#f5f5f5] uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                  >
                    执行突袭
                  </button>
                </div>
              }
            />

            {/* Skill 2: Bloodlust Instinct */}
            <SkillCard
              title="残夜密言 ∙ 狂嗜渴血"
              subtitle="WOLFPACK COMPACT"
              description="同伴可在夜色中共享低语，集结票数，在暗夜猎杀中对同一位目标展开毁灭性伤害。"
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
              title="怒膛轰击 ∙ 终局猎杀"
              subtitle="VENGEFUL BULLET"
              description={
                !isUserDead
                  ? "🔫 当你在白天表决中被流放（或在夜间逝去）时，猎枪的最后一颗子弹将怒火出击，击穿一个仇敌。"
                  : (selectedCardId === null 
                    ? "☠️ 你已被清除！猎枪子弹在枪口通红闪烁！请在圆座上锁定一名陪葬卡牌，射杀他！"
                    : `🎯 已校准准心：[玩家 ${selectedCardId} 号]！点击右侧按钮，扣动扳机送其上绞架！`)
              }
              type="主动"
              status={isUserDead ? "就绪" : "锁定"}
              icon={Crosshair}
              glowColor="shadow-yellow-500/20"
              actionButton={
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <TargetDropdown
                    currentVal={selectedCardId}
                    onChange={(id) => setSelectedCardId(id)}
                    filterFn={(p) => p.isAlive && !p.isUser}
                  />
                  <button
                    onClick={() => selectedCardId && executeHunterShoot(selectedCardId)}
                    disabled={selectedCardId === null}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:cursor-not-allowed border-2 border-red-800 rounded font-sans font-black text-[9px] text-white uppercase tracking-wider cursor-pointer shadow-lg active:scale-95 transition-all text-center"
                  >
                    扣动扳机
                  </button>
                </div>
              }
            />

            {/* Skill 2: Steel Will */}
            <SkillCard
              title="铁骨精金 ∙ 誓约意志"
              subtitle="STEEL RESILIENCE"
              description="如果你遭受凶残狼人晚间撕咬，你依然处于武装威慑。若遭受女巫阴险的绝情毒药，则禁忌被锁孔，不可鸣枪。"
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
