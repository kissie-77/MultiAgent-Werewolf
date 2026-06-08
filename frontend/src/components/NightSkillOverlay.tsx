import React, { useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useGameStore } from "../store";
import type { SkillFx } from "../types";

/** Duration (ms) the overlay stays visible before auto-dismissing. */
const OVERLAY_MS = 3200;

/**
 * Visual theme per action type — icon, colors, border glow, result handling.
 */
interface SkillTheme {
  icon: string;
  label: string;
  accent: string;
  border: string;
  glow: string;
  bg: string;
  resultLabel?: (r: string) => string;
}

const SKILL_THEME: Record<string, SkillTheme> = {
  seer_checked: {
    icon: "🔮",
    label: "预言家查验",
    accent: "text-cyan-300",
    border: "border-cyan-500/60",
    glow: "rgba(6,182,212,0.5)",
    bg: "bg-cyan-950/30",
    resultLabel: (r) => (r === "狼人" ? "身份：狼人" : "身份：好人"),
  },
  werewolf_killed: {
    icon: "🐺",
    label: "狼人击杀",
    accent: "text-red-400",
    border: "border-red-500/60",
    glow: "rgba(239,68,68,0.5)",
    bg: "bg-red-950/30",
  },
  white_wolf_killed: {
    icon: "🐺",
    label: "白狼王击杀",
    accent: "text-red-300",
    border: "border-red-400/60",
    glow: "rgba(248,113,113,0.5)",
    bg: "bg-red-950/30",
  },
  witch_saved: {
    icon: "💊",
    label: "女巫救人",
    accent: "text-purple-300",
    border: "border-purple-500/60",
    glow: "rgba(168,85,247,0.5)",
    bg: "bg-purple-950/30",
  },
  witch_poison_used: {
    icon: "☠️",
    label: "女巫用毒",
    accent: "text-purple-400",
    border: "border-purple-500/60",
    glow: "rgba(168,85,247,0.5)",
    bg: "bg-purple-950/30",
  },
  witch_poisoned: {
    icon: "☠️",
    label: "女巫毒杀",
    accent: "text-purple-400",
    border: "border-purple-500/60",
    glow: "rgba(168,85,247,0.5)",
    bg: "bg-purple-950/30",
  },
  guard_protected: {
    icon: "🛡️",
    label: "守卫守护",
    accent: "text-emerald-300",
    border: "border-emerald-500/60",
    glow: "rgba(16,185,129,0.5)",
    bg: "bg-emerald-950/30",
  },
  lovers_linked: {
    icon: "💕",
    label: "恋人连结",
    accent: "text-pink-300",
    border: "border-pink-500/60",
    glow: "rgba(236,72,153,0.5)",
    bg: "bg-pink-950/30",
  },
  wolf_beauty_charmed: {
    icon: "💋",
    label: "狼美人魅惑",
    accent: "text-rose-300",
    border: "border-rose-500/60",
    glow: "rgba(244,63,94,0.5)",
    bg: "bg-rose-950/30",
  },
  nightmare_blocked: {
    icon: "🌑",
    label: "梦魇封锁",
    accent: "text-indigo-300",
    border: "border-indigo-500/60",
    glow: "rgba(99,102,241,0.5)",
    bg: "bg-indigo-950/30",
  },
  guardian_wolf_protected: {
    icon: "🐺",
    label: "守墓狼保护",
    accent: "text-red-300",
    border: "border-red-400/60",
    glow: "rgba(248,113,113,0.5)",
    bg: "bg-red-950/30",
  },
  raven_marked: {
    icon: "🐦‍⬛",
    label: "乌鸦标记",
    accent: "text-slate-300",
    border: "border-slate-400/60",
    glow: "rgba(148,163,184,0.4)",
    bg: "bg-slate-900/30",
  },
  graveyard_keeper_check: {
    icon: "⚰️",
    label: "守墓人查验",
    accent: "text-stone-300",
    border: "border-stone-400/60",
    glow: "rgba(168,162,158,0.4)",
    bg: "bg-stone-900/30",
    resultLabel: (r) => `查验结果：${r}`,
  },
  magician_swapped: {
    icon: "🎩",
    label: "魔术师换牌",
    accent: "text-fuchsia-300",
    border: "border-fuchsia-500/60",
    glow: "rgba(217,70,239,0.5)",
    bg: "bg-fuchsia-950/30",
  },
};

const DEFAULT_THEME: SkillTheme = {
  icon: "✨",
  label: "夜间行动",
  accent: "text-zinc-300",
  border: "border-zinc-500/60",
  glow: "rgba(161,161,170,0.4)",
  bg: "bg-zinc-900/30",
};

/** Build the description text for the overlay. */
function buildDesc(fx: SkillFx, theme: typeof DEFAULT_THEME): string {
  const target = fx.targetName || (fx.targetSeat != null ? `${fx.targetSeat}号` : "");
  const parts: string[] = [];

  switch (fx.actionType) {
    case "seer_checked":
      parts.push(`查验了 ${target}`);
      if (fx.result && theme.resultLabel) parts.push(theme.resultLabel(fx.result));
      break;
    case "werewolf_killed":
    case "white_wolf_killed":
      parts.push(`击杀了 ${target}`);
      break;
    case "witch_saved":
      parts.push(`使用解药救治了 ${target}`);
      break;
    case "witch_poison_used":
    case "witch_poisoned":
      parts.push(`对 ${target} 使用了毒药`);
      break;
    case "guard_protected":
      parts.push(`守护了 ${target}`);
      break;
    case "lovers_linked":
      parts.push(`将 ${target} 连结为恋人`);
      break;
    case "wolf_beauty_charmed":
      parts.push(`魅惑了 ${target}`);
      break;
    case "nightmare_blocked":
      parts.push(`封锁了 ${target} 的技能`);
      break;
    case "guardian_wolf_protected":
      parts.push(`保护了 ${target}`);
      break;
    case "raven_marked":
      parts.push(`标记了 ${target}`);
      break;
    case "graveyard_keeper_check":
      parts.push(`查验了 ${target}`);
      if (fx.result && theme.resultLabel) parts.push(theme.resultLabel(fx.result));
      break;
    case "magician_swapped":
      parts.push(`交换了 ${target}`);
      break;
    default:
      parts.push(target ? `行动：${target}` : "行动完成");
  }

  return parts.join("，");
}

/** Determine if the result should be shown with special emphasis. */
function isResultBad(fx: SkillFx): boolean {
  return fx.result === "狼人";
}

export default function NightSkillOverlay() {
  const skillFx = useGameStore((s) => s.state?.skillFx);
  const clearSkillFx = useGameStore((s) => s.clearSkillFx);

  // Auto-dismiss after OVERLAY_MS
  useEffect(() => {
    if (!skillFx) return;
    const t = setTimeout(() => clearSkillFx(), OVERLAY_MS);
    return () => clearTimeout(t);
  }, [skillFx?.nonce, clearSkillFx]);

  if (!skillFx) return null;

  const theme = SKILL_THEME[skillFx.actionType] ?? DEFAULT_THEME;
  const desc = buildDesc(skillFx, theme);
  const bad = isResultBad(skillFx);

  return (
    <AnimatePresence>
      {skillFx && (
        <motion.div
          key={skillFx.nonce}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35 }}
          className="fixed inset-0 z-[115] pointer-events-none flex items-center justify-center p-6"
        >
          {/* Background vignette */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />

          {/* Skill card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.7, y: 40 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 1.05, y: -20 }}
            transition={{ type: "spring", stiffness: 320, damping: 24 }}
            className={`relative ${theme.bg} backdrop-blur-md border ${theme.border} rounded-lg p-6 flex flex-col items-center justify-center select-none overflow-hidden min-w-[280px]`}
            style={{ boxShadow: `0 0 80px ${theme.glow}, 0 0 30px ${theme.glow}` }}
          >
            {/* Top accent bar */}
            <div
              className="absolute top-0 inset-x-0 h-1"
              style={{ backgroundColor: theme.glow.replace(/[\d.]+\)$/, "1)"), boxShadow: `0 0 12px ${theme.glow}` }}
            />
            {/* Bottom accent bar */}
            <div
              className="absolute bottom-0 inset-x-0 h-1"
              style={{ backgroundColor: theme.glow.replace(/[\d.]+\)$/, "1)"), boxShadow: `0 0 12px ${theme.glow}` }}
            />

            {/* Icon */}
            <motion.span
              initial={{ scale: 0, rotate: -30 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 15, delay: 0.1 }}
              className="text-5xl mb-3 relative z-10"
            >
              {theme.icon}
            </motion.span>

            {/* Label */}
            <span className={`font-serif text-sm tracking-[0.4em] uppercase mb-1 relative z-10 ${theme.accent} font-bold`}>
              {theme.label}
            </span>

            {/* Seat number */}
            <span className="font-mono text-[10px] text-zinc-500 tracking-widest relative z-10 mb-2">
              {skillFx.seat}号位
            </span>

            {/* Description */}
            <span className={`font-sans text-base tracking-wider relative z-10 ${bad ? "text-red-300 font-black" : "text-zinc-100"}`}>
              {desc}
            </span>

            {/* Result badge for seer / graveyard keeper */}
            {skillFx.result && (skillFx.actionType === "seer_checked" || skillFx.actionType === "graveyard_keeper_check") && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, type: "spring", stiffness: 300, damping: 20 }}
                className={`mt-3 px-4 py-1.5 rounded border relative z-10 font-sans font-black text-sm tracking-widest ${
                  bad
                    ? "bg-red-950/80 border-red-500/60 text-red-300"
                    : "bg-cyan-950/80 border-cyan-500/60 text-cyan-300"
                }`}
              >
                {bad ? "狼人" : "好人"}
              </motion.div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
