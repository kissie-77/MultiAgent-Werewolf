import { Moon, Sun, Hourglass } from "lucide-react";
import { useGameStore } from "../store";
import { stageBadge } from "../lib/phaseStage";

/** Per-stage concrete color tokens (avoids Tailwind opacity-on-currentColor utilities). */
const THEME = {
  moon: {
    box: "border-violet-500/70 shadow-[0_0_16px_rgba(139,92,246,0.45)]",
    icon: "text-violet-200",
    day: "text-violet-50",
    phase: "text-violet-300/80",
  },
  sun: {
    box: "border-amber-500/70 shadow-[0_0_16px_rgba(245,158,11,0.45)]",
    icon: "text-amber-200",
    day: "text-amber-50",
    phase: "text-amber-300/80",
  },
  wait: {
    box: "border-zinc-600/70 shadow-[0_0_12px_rgba(82,82,91,0.4)]",
    icon: "text-zinc-300",
    day: "text-zinc-100",
    phase: "text-zinc-400",
  },
} as const;

export default function PhaseBadge() {
  const phase = useGameStore((s) => s.state?.phase);
  const dayNumber = useGameStore((s) => s.state?.dayNumber ?? 0);
  if (!phase) return null;

  const badge = stageBadge(phase, dayNumber);
  const theme = THEME[badge.icon];

  return (
    <div className="absolute top-16 left-4 z-30 pointer-events-none select-none">
      <div className={`flex items-center gap-3 bg-black/55 backdrop-blur-md border rounded-lg px-3.5 py-2 ${theme.box}`}>
        <div className={`w-9 h-9 rounded-full bg-black/60 border border-zinc-700/50 flex items-center justify-center shrink-0 ${theme.icon}`}>
          {badge.icon === "moon" ? (
            <Moon className="w-5 h-5 animate-pulse" />
          ) : badge.icon === "wait" ? (
            <Hourglass className="w-5 h-5 animate-spin" style={{ animationDuration: "3s" }} />
          ) : (
            <Sun className="w-5 h-5 animate-spin-slow" />
          )}
        </div>
        <div className="flex flex-col leading-tight">
          <span className={`font-serif font-black text-sm tracking-wider ${theme.day}`}>{badge.dayText}</span>
          <span className={`font-mono text-[10px] uppercase tracking-widest ${theme.phase}`}>
            {badge.phaseText}
          </span>
        </div>
      </div>
    </div>
  );
}
