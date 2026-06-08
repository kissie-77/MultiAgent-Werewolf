import { useEffect, useRef } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { Moon, Sun, Skull } from "lucide-react";
import { useGameStore } from "../store";
import {
  coarseStage,
  shouldShowCard,
  stageCardText,
  MIN_GAP_MS,
  CARD_MS,
  DAY_DEATH_DELAY_MS,
  type CoarseStage,
} from "../lib/phaseStage";

export default function PhaseTransitionCard() {
  const phase = useGameStore((s) => s.state?.phase);
  const dayNumber = useGameStore((s) => s.state?.dayNumber ?? 0);
  const victimId = useGameStore((s) => s.state?.victimId ?? null);
  const stageFx = useGameStore((s) => s.stageFx);
  const fireStageFx = useGameStore((s) => s.fireStageFx);
  const clearStageFx = useGameStore((s) => s.clearStageFx);
  const reduce = useReducedMotion();

  // --- Detector: coarse-stage boundary -> fireStageFx -------------------
  const prevStageRef = useRef<CoarseStage | null>(null);
  const lastChangeTsRef = useRef<number>(performance.now());
  const dayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!phase) return;
    const next = coarseStage(phase);
    if (prevStageRef.current === null) {
      // First observation after mount: latch without firing.
      prevStageRef.current = next;
      lastChangeTsRef.current = performance.now();
      return;
    }
    const prev = prevStageRef.current;
    if (prev === next) return;
    const now = performance.now();
    const gap = now - lastChangeTsRef.current;
    prevStageRef.current = next;
    lastChangeTsRef.current = now;

    if (!shouldShowCard(prev, next, gap, MIN_GAP_MS)) return;

    if (next === "day") {
      // Delay so a same-tick player_died has been reduced -> merge into one card.
      if (dayTimerRef.current) clearTimeout(dayTimerRef.current);
      dayTimerRef.current = setTimeout(() => fireStageFx("day"), DAY_DEATH_DELAY_MS);
    } else {
      fireStageFx(next);
    }
  }, [phase, fireStageFx]);

  useEffect(() => () => { if (dayTimerRef.current) clearTimeout(dayTimerRef.current); }, []);

  // --- Auto-dismiss the card -------------------------------------------
  useEffect(() => {
    if (!stageFx) return;
    const t = setTimeout(() => clearStageFx(), CARD_MS);
    return () => clearTimeout(t);
  }, [stageFx?.nonce, clearStageFx]);

  const card = stageFx ? stageCardText(stageFx.stage, dayNumber, victimId) : null;
  const isNight = stageFx?.stage === "night";

  // Flash tint: warm bloom for dawn, deep darken for nightfall.
  const flashClass = isNight
    ? "bg-[radial-gradient(ellipse_at_center,_rgba(20,8,40,0.0),_rgba(8,2,18,0.85))]"
    : card?.death
      ? "bg-[radial-gradient(ellipse_at_center,_rgba(120,10,10,0.0),_rgba(80,6,6,0.7))]"
      : "bg-[radial-gradient(ellipse_at_center,_rgba(255,210,140,0.18),_rgba(120,60,8,0.0))]";

  return (
    <AnimatePresence>
      {stageFx && card && (
        <motion.div
          key={stageFx.nonce}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0.15 : 0.35 }}
          className="fixed inset-0 z-[110] pointer-events-none flex items-center justify-center"
        >
          {/* one-shot flash / darken layer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: reduce ? 0.5 : [0, 1, 0.55] }}
            transition={{ duration: reduce ? 0.2 : 0.9, times: reduce ? undefined : [0, 0.25, 1] }}
            className={`absolute inset-0 ${flashClass}`}
          />
          {/* centered woodcut title (light vignette, lets the camera move read through) */}
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.92, y: 18 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 1.04, y: -14 }}
            transition={{ type: "spring", stiffness: 260, damping: 26 }}
            className="relative flex flex-col items-center select-none px-10 py-6"
          >
            {isNight ? (
              <Moon className="w-12 h-12 text-violet-300 drop-shadow-[0_0_18px_rgba(168,85,247,0.8)] mb-2" />
            ) : card.death ? (
              <Skull className="w-12 h-12 text-red-400 drop-shadow-[0_0_18px_rgba(220,38,38,0.8)] mb-2 animate-pulse" />
            ) : (
              <Sun className="w-12 h-12 text-amber-300 drop-shadow-[0_0_18px_rgba(251,191,36,0.85)] mb-2" />
            )}
            <span
              className={`font-serif text-sm tracking-[0.6em] uppercase font-black mb-1 ${
                isNight ? "text-violet-300/90" : card.death ? "text-red-400/90" : "text-amber-300/90"
              }`}
            >
              {card.kicker}
            </span>
            <h1
              className={`font-sans font-black text-5xl tracking-widest ${
                isNight ? "text-violet-50" : "text-amber-50"
              } drop-shadow-[0_2px_24px_rgba(0,0,0,0.9)]`}
            >
              {card.title}
            </h1>
            <span
              className={`font-mono text-xs tracking-[0.4em] mt-2 ${
                card.death ? "text-red-300 font-black" : "text-zinc-300/80"
              }`}
            >
              · {card.sub} ·
            </span>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
