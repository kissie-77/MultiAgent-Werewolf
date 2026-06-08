import React, { useEffect, useState } from "react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { getTarotImage } from "../utils/roles";

/** Per-effect accent color (card glow + ambient flash) and particle tint. */
function themeFor(effectType: string): { accentColor: string; particleColor: string } {
  switch (effectType) {
    case "inspect": return { accentColor: "#a855f7", particleColor: "bg-purple-400" };
    case "heal": return { accentColor: "#f43f5e", particleColor: "bg-rose-400" };
    case "poison": return { accentColor: "#10b981", particleColor: "bg-emerald-400" };
    case "bite": return { accentColor: "#ef4444", particleColor: "bg-red-500" };
    case "shoot": return { accentColor: "#eab308", particleColor: "bg-yellow-400" };
    default: return { accentColor: "#3b82f6", particleColor: "bg-blue-400" }; // vote / rally
  }
}

/** Cinzel latin tagline under the Chinese skill name. */
const LATIN: Record<string, string> = {
  inspect: "SEER · ILLUMINATION",
  heal: "WITCH · ELIXIR",
  poison: "WITCH · VENOM",
  bite: "WEREWOLF · BLOODLUST",
  shoot: "HUNTER · STEEL BOLT",
  vote: "VILLAGER · VERDICT",
  rally: "ARCANA · FATE",
};

export default function CastSkillOverlay() {
  const activeCast = useGameStore((state) => state.activeCast);
  const clearCast = useGameStore((state) => state.clearCast);
  const [particleList, setParticleList] = useState<
    { id: number; x: number; y: number; speed: number; size: number }[]
  >([]);

  // Trigger SFX + particles on each new cast, then auto-dismiss.
  useEffect(() => {
    if (!activeCast) return;

    setParticleList(
      Array.from({ length: 25 }).map((_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100 + 50,
        speed: Math.random() * 3 + 1,
        size: Math.random() * 6 + 2,
      })),
    );

    const timer = setTimeout(() => clearCast?.(), 2500);
    return () => clearTimeout(timer);
  }, [activeCast, clearCast]);

  if (!activeCast) return null;

  const { role, skillName, casterName, targetName, effectType, targetId, targetVerb } = activeCast;
  const theme = themeFor(effectType);
  const latin = LATIN[effectType] ?? "ARCANA · FATE";

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-950/90 select-none cursor-pointer"
        onClick={() => clearCast?.()}
        id="cast-skill-screen-overlay"
      >
        {/* Particle ambient layer */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {particleList.map((p) => (
            <motion.div
              key={p.id}
              className={`absolute rounded-full opacity-60 ${theme.particleColor} pointer-events-none`}
              style={{ width: p.size, height: p.size, left: `${p.x}%`, bottom: `${p.y - 45}%` }}
              animate={{ y: [0, -320], opacity: [0.7, 1, 0], scale: [1, 1.4, 0.4] }}
              transition={{ duration: p.speed, repeat: Infinity, ease: "linear" }}
            />
          ))}
        </div>

        {/* Ambient colored flash */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          className="absolute inset-0 pointer-events-none opacity-40"
          style={{ background: `radial-gradient(circle, ${theme.accentColor}44 0%, transparent 70%)` }}
        />

        {/* Diagonal slashing strikes for any wolf-camp bite */}
        {effectType === "bite" && (
          <div className="absolute inset-0 flex flex-col justify-center items-center pointer-events-none overflow-hidden z-[25]">
            <motion.div
              initial={{ scaleX: 0, opacity: 0, x: -300, y: -200 }}
              animate={{ scaleX: 1, opacity: [0, 1, 1, 0], x: 300, y: 200 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="w-[150%] h-4 bg-red-600 rotate-[35deg] blur-sm shrink-0"
            />
            <motion.div
              initial={{ scaleX: 0, opacity: 0, x: 300, y: -200 }}
              animate={{ scaleX: 1, opacity: [0, 1, 1, 0], x: -300, y: 200 }}
              transition={{ duration: 0.5, delay: 0.15, ease: "easeOut" }}
              className="w-[150%] h-4 bg-red-600 rotate-[-35deg] blur-sm shrink-0"
            />
          </div>
        )}

        {/* Gunshot muzzle flash for hunter shoot */}
        {effectType === "shoot" && (
          <motion.div
            initial={{ scale: 0.3, opacity: 0 }}
            animate={{ scale: [1, 15], opacity: [0, 1, 0] }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="absolute inset-0 pointer-events-none z-30 bg-radial from-amber-500 via-orange-950 to-transparent flex items-center justify-center rounded-full"
            style={{ width: 120, height: 120, left: "calc(50% - 60px)", top: "calc(50% - 60px)" }}
          />
        )}

        {/* Center stack: full tarot card + name plate below */}
        <div className="relative z-10 flex flex-col items-center justify-center gap-5 pointer-events-auto px-4">
          {/* Full tarot card — uncropped (~60vh ≈ quarter screen), flips in like a drawn card */}
          <div style={{ perspective: 1200 }}>
            <motion.div
              initial={{ rotateY: 90, scale: 0.7, opacity: 0, y: 30 }}
              animate={{ rotateY: 0, scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.6, opacity: 0 }}
              transition={{ type: "spring", stiffness: 140, damping: 16 }}
            >
              <img
                src={getTarotImage(role)}
                alt={role}
                draggable={false}
                className="h-[60vh] w-auto max-w-[92vw] object-contain rounded-xl"
                style={{
                  filter: `drop-shadow(0 0 38px ${theme.accentColor}aa) drop-shadow(0 12px 26px rgba(0,0,0,0.85))`,
                }}
              />
            </motion.div>
          </div>

          {/* Name plate */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28, duration: 0.45 }}
            className="flex flex-col items-center gap-1.5 text-center"
          >
            <h2
              className="font-sans font-black text-3xl sm:text-4xl tracking-[0.22em] text-transparent bg-clip-text bg-gradient-to-b from-amber-100 via-amber-300 to-amber-600 leading-tight"
              style={{ textShadow: "0 2px 18px rgba(245,158,11,0.35)" }}
            >
              {skillName}
            </h2>

            <span className="font-serif text-[11px] sm:text-xs uppercase tracking-[0.42em] text-amber-500/70">
              {latin}
            </span>

            <span className="font-sans text-sm text-zinc-300/90 mt-1 tracking-wide">
              <span className="font-bold" style={{ color: theme.accentColor }}>
                {casterName}
              </span>
              {targetName && (
                <>
                  {" "}
                  {targetVerb}了{" "}
                  <span className="text-zinc-100 font-bold">{targetName}</span>
                  {targetId != null ? `（${targetId}号）` : ""}
                </>
              )}
            </span>
          </motion.div>

          <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-[0.2em] mt-1">
            点击任意区域或等待法阵消散收回卡牌
          </span>
        </div>
      </div>
    </AnimatePresence>
  );
}
