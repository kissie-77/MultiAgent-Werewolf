import React from "react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { Skull } from "lucide-react";

export default function DeathAlertPanel() {
  const phase = useGameStore((state) => state.state?.phase);
  const victimId = useGameStore((state) => state.state?.victimId);

  const isMurderAlert = phase === "DAY_ANNOUNCEMENT" && victimId !== null;

  return (
    <AnimatePresence>
      {isMurderAlert && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8, y: 50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 1.1 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className="fixed inset-0 z-[120] pointer-events-none flex items-center justify-center p-6 bg-red-950/40 backdrop-blur-sm"
        >
          {/* Subtle vignette/scanline overlay */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent,_rgba(127,29,29,0.8))] mix-blend-overlay pointer-events-none" />

          {/* Alert Card */}
          <motion.div 
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
            className="relative bg-zinc-950 border border-red-800 p-8 rounded shadow-[0_0_80px_rgba(220,38,38,0.6)] flex flex-col items-center justify-center select-none overflow-hidden"
          >
            {/* Pulsing red scanlines inside */}
            <div className="absolute inset-0 bg-red-900/10 pointer-events-none bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(220,38,38,0.1)_2px,rgba(220,38,38,0.1)_4px)]" />

            {/* Glowing red accent bars */}
            <div className="absolute top-0 inset-x-0 h-1 bg-red-600 shadow-[0_0_10px_rgba(220,38,38,1)]" />
            <div className="absolute bottom-0 inset-x-0 h-1 bg-red-600 shadow-[0_0_10px_rgba(220,38,38,1)]" />
            
            <Skull className="w-16 h-16 text-red-500 animate-pulse mb-4 relative z-10" />
            
            <span className="font-serif text-red-500 text-sm tracking-[0.5em] uppercase mb-1 relative z-10">血色黎明</span>
            <h1 className="font-sans font-black text-4xl text-red-100 tracking-wider mb-2 relative z-10 drop-shadow-[0_0_10px_rgba(220,38,38,0.8)]">
              【{victimId}号】已遇害
            </h1>
            <p className="font-mono text-zinc-400 text-xs tracking-widest relative z-10">
              昨夜，死亡的阴影降临了此席位...
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
