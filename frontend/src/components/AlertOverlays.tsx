import React, { useEffect, useState } from "react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { Shield } from "lucide-react";

// Note: the night-death reveal is now merged into the daybreak card
// (see PhaseTransitionCard). This overlay only owns the sheriff-elected card.
export default function AlertOverlays() {
  const sheriffId = useGameStore((state) => state.state?.sheriffId);

  const [showSheriffAlert, setShowSheriffAlert] = useState(false);
  const [newSheriff, setNewSheriff] = useState<number | null>(null);

  // 使用 ref 跟踪上次处理的警长，防止无限循环和过早取消超时
  const lastProcessedSheriffRef = React.useRef<number | null | undefined>(null);

  useEffect(() => {
    if (sheriffId !== undefined && sheriffId !== null && sheriffId !== lastProcessedSheriffRef.current) {
      setNewSheriff(sheriffId);
      setShowSheriffAlert(true);
      lastProcessedSheriffRef.current = sheriffId;

      const t = setTimeout(() => setShowSheriffAlert(false), 5000);
      return () => clearTimeout(t);
    }
  }, [sheriffId]);

  return (
    <AnimatePresence>
      {showSheriffAlert && newSheriff !== null && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
          className="fixed inset-0 z-[120] pointer-events-none flex items-center justify-center p-6 bg-yellow-950/40 backdrop-blur-sm"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 50 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 1.1 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent,_rgba(161,98,7,0.8))] mix-blend-overlay pointer-events-none"
          />

          <motion.div
            initial={{ scaleY: 0 }}
            animate={{ scaleY: 1 }}
            exit={{ opacity: 0, scale: 0.8, y: -20 }}
            transition={{ delay: 0.1, duration: 0.5, type: "spring", bounce: 0.5 }}
            className="relative bg-zinc-950 border border-yellow-600 p-8 rounded shadow-[0_0_100px_rgba(234,179,8,0.6)] flex flex-col items-center justify-center select-none overflow-hidden"
          >
            <div className="absolute inset-0 bg-yellow-900/10 pointer-events-none" />

            <div className="absolute top-0 inset-x-0 h-1.5 bg-yellow-500 shadow-[0_0_15px_rgba(234,179,8,1)]" />
            <div className="absolute bottom-0 inset-x-0 h-1.5 bg-yellow-500 shadow-[0_0_15px_rgba(234,179,8,1)]" />

            <Shield className="w-20 h-20 text-yellow-500 mb-4 relative z-10 drop-shadow-[0_0_15px_rgba(234,179,8,0.8)]" />

            <span className="font-serif text-yellow-500 text-sm tracking-[0.5em] uppercase mb-1 relative z-10 font-bold">无上殊荣</span>
            <h1 className="font-sans font-black text-4xl text-yellow-100 tracking-wider mb-2 relative z-10 drop-shadow-[0_0_10px_rgba(234,179,8,0.8)]">
              【 {newSheriff} 号 】当选警长
            </h1>
            <p className="font-mono text-zinc-300 text-base tracking-widest relative z-10 mt-3 font-bold bg-yellow-950/80 px-4 py-2 rounded border border-yellow-800/50">
              1.5 归票特权启动
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
