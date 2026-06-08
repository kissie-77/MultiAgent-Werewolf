import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Moon, ChevronDown, ChevronUp } from "lucide-react";
import { useGameStore } from "../store";
import { isRoleRevealed } from "../lib/humanPrompt";
import type { NightActionEntry } from "../types";
import type { ColorScheme } from "./RightPanelColumn";

/* ─── NightActionLog color scheme ─── */
const LOG_COLORS: Record<
  ColorScheme,
  {
    header: string;
    icon: string;
    iconDim: string;
    body: string;
    dot: string;
    text: string;
    shadow: string;
  }
> = {
  emerald: {
    header: "border-emerald-700/50 text-emerald-300",
    icon: "text-emerald-400",
    iconDim: "text-emerald-500",
    body: "border-emerald-900/50 bg-black/60 backdrop-blur-md",
    dot: "bg-emerald-600",
    text: "text-emerald-500/70",
    shadow: "rgba(5,150,105,0.1)",
  },
  violet: {
    header: "border-violet-900/50 text-violet-300",
    icon: "text-violet-400",
    iconDim: "text-violet-500",
    body: "border-violet-900/50 bg-black/60 backdrop-blur-md",
    dot: "bg-violet-600",
    text: "text-violet-500/70",
    shadow: "rgba(109,40,217,0.1)",
  },
  amber: {
    header: "border-amber-700/50 text-amber-300",
    icon: "text-amber-400",
    iconDim: "text-amber-500",
    body: "border-amber-900/50 bg-black/60 backdrop-blur-md",
    dot: "bg-amber-600",
    text: "text-amber-500/70",
    shadow: "rgba(217,119,6,0.1)",
  },
  rose: {
    header: "border-rose-800/50 text-rose-300",
    icon: "text-rose-400",
    iconDim: "text-rose-500",
    body: "border-rose-900/50 bg-black/60 backdrop-blur-md",
    dot: "bg-rose-600",
    text: "text-rose-500/70",
    shadow: "rgba(190,18,60,0.1)",
  },
};

/** Icon and label for each night action type. */
const ACTION_META: Record<string, { icon: string; label: string; color: string }> = {
  seer_checked: { icon: "🔮", label: "预言家查验", color: "text-cyan-400" },
  witch_saved: { icon: "💊", label: "女巫救人", color: "text-purple-400" },
  witch_poison_used: { icon: "☠️", label: "女巫用毒", color: "text-purple-400" },
  witch_poisoned: { icon: "☠️", label: "女巫毒杀", color: "text-purple-400" },
  werewolf_killed: { icon: "🐺", label: "狼人击杀", color: "text-red-400" },
  guard_protected: { icon: "🛡️", label: "守卫守护", color: "text-emerald-400" },
  lovers_linked: { icon: "💕", label: "恋人连结", color: "text-pink-400" },
  white_wolf_killed: { icon: "🐺⚪", label: "白狼王击杀", color: "text-red-300" },
  wolf_beauty_charmed: { icon: "🐺💋", label: "狼美人魅惑", color: "text-rose-400" },
  nightmare_blocked: { icon: "🌑", label: "梦魇封锁", color: "text-indigo-400" },
  guardian_wolf_protected: { icon: "🐺🛡️", label: "守墓狼保护", color: "text-red-300" },
  raven_marked: { icon: "🐦‍⬛", label: "乌鸦标记", color: "text-slate-300" },
  graveyard_keeper_check: { icon: "⚰️", label: "守墓人查验", color: "text-stone-400" },
  magician_swapped: { icon: "🎩", label: "魔术师换牌", color: "text-fuchsia-400" },
};

function buildActionText(entry: NightActionEntry): string {
  const { actionType, targetName, result, seat } = entry;
  switch (actionType) {
    case "seer_checked":
      return result ? `查验了 ${targetName}，身份：${result === "好人" ? "好人" : "狼人"}` : `查验了 ${targetName}`;
    case "witch_saved":
      return `使用解药救治了 ${targetName}`;
    case "witch_poison_used":
      return `对 ${targetName} 使用了毒药`;
    case "witch_poisoned":
      return `毒杀了 ${targetName}`;
    case "werewolf_killed":
      return `击杀了 ${targetName}`;
    case "guard_protected":
      return `守护了 ${targetName}`;
    case "lovers_linked":
      return `将 ${targetName} 连结为恋人`;
    case "white_wolf_killed":
      return `击杀了 ${targetName}`;
    case "wolf_beauty_charmed":
      return `魅惑了 ${targetName}`;
    case "nightmare_blocked":
      return `封锁了 ${targetName} 的技能`;
    case "guardian_wolf_protected":
      return `保护了 ${targetName}`;
    case "raven_marked":
      return `标记了 ${targetName}`;
    case "graveyard_keeper_check":
      return result ? `查验了 ${targetName}：${result}` : `查验了 ${targetName}`;
    case "magician_swapped":
      return `交换了 ${targetName}`;
    default:
      return `行动：${targetName}`;
  }
}

const ActionItem = React.memo(function ActionItem({
  entry,
  showRole,
}: {
  entry: NightActionEntry;
  showRole: boolean;
}) {
  const meta = ACTION_META[entry.actionType] ?? { icon: "❓", label: entry.actionType, color: "text-zinc-400" };
  const desc = buildActionText(entry);

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
      className="flex items-start gap-2 py-1.5"
    >
      <span className="text-sm shrink-0 mt-0.5">{meta.icon}</span>
      <div className="flex flex-col min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`font-mono text-[11px] font-black tracking-wider uppercase ${meta.color}`}>
            {meta.label}
          </span>
          <span className="font-mono text-[9px] text-zinc-500">
            {entry.seat}号
          </span>
          {showRole && entry.role && (
            <span className={`font-mono text-[9px] px-1 py-0.5 rounded border ${meta.color.replace("text-", "border-")}/30 ${meta.color} bg-black/40`}>
              {entry.role}
            </span>
          )}
        </div>
        <span className="font-sans text-[11px] text-zinc-300 leading-snug">
          {desc}
        </span>
      </div>
    </motion.div>
  );
});

export default React.memo(function NightActionLog({
  colorScheme = "violet",
  defaultOpen = true,
}: {
  colorScheme?: ColorScheme;
  defaultOpen?: boolean;
}) {
  const nightActionLog = useGameStore((s) => s.state?.nightActionLog ?? []);
  const phase = useGameStore((s) => s.state?.phase);
  const humanSeat = useGameStore((s) => s.humanSeat);
  const isSeatView = humanSeat != null;
  const [collapsed, setCollapsed] = useState(!defaultOpen);
  const cc = LOG_COLORS[colorScheme];

  const isNight = phase?.startsWith("NIGHT") ?? false;

  // Dedupe by id (show all night actions across all rounds)
  const seen = new Set<number>();
  const uniqueActions = nightActionLog.filter((e) => {
    if (seen.has(e.id)) return false;
    seen.add(e.id);
    return true;
  });

  const showRole = (seat: number, role: string) =>
    !isSeatView || seat === humanSeat || isRoleRevealed(role);

  const hasContent = uniqueActions.length > 0;

  return (
    <div className="w-full pointer-events-auto">
      {/* Toggle button — always visible */}
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className={`w-full flex items-center justify-between px-3 py-2 bg-black/60 border ${cc.header} rounded-t-xl hover:bg-black/70 transition-colors cursor-pointer`}
      >
        <div className="flex items-center gap-2">
          <Moon className={`w-3.5 h-3.5 ${isNight ? "animate-pulse " + cc.icon : cc.iconDim}`} />
          <span className="font-serif text-[11px] font-black tracking-[0.2em] uppercase">
            暗夜行迹
          </span>
          {!isNight && hasContent && (
            <span className="font-mono text-[9px] text-zinc-500">（昼间可查）</span>
          )}
        </div>
        {collapsed ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
      </button>

      {/* Collapsible content */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            key="night-action-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className={`${cc.body} border-x border-b rounded-b-xl px-3 py-2 min-w-0`}
              style={{ boxShadow: `0 0 20px ${cc.shadow}` }}>
              {!hasContent ? (
                <div className="py-3 flex items-center justify-center gap-2">
                  <div className="flex gap-1">
                    <div className={`w-1 h-1 ${cc.dot} rounded-full animate-bounce`} />
                    <div className={`w-1 h-1 ${cc.dot} rounded-full animate-bounce [animation-delay:150ms]`} />
                    <div className={`w-1 h-1 ${cc.dot} rounded-full animate-bounce [animation-delay:300ms]`} />
                  </div>
                  <span className={`font-mono text-[10px] ${cc.text} tracking-wider`}>
                    {isNight ? "等待夜色中的行动..." : "暂无行动记录"}
                  </span>
                </div>
              ) : (
                <div className="max-h-[300px] overflow-y-auto">
                  <AnimatePresence initial={false}>
                    {uniqueActions.map((entry) => (
                      <ActionItem
                        key={entry.id}
                        entry={entry}
                        showRole={showRole(entry.seat, entry.role)}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});
