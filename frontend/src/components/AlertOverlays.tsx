import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Shield, Skull } from "lucide-react";
import { useGameStore } from "../store";

export default function AlertOverlays() {
  const phase = useGameStore((state) => state.state?.phase);
  const victimId = useGameStore((state) => state.state?.victimId);
  const sheriffId = useGameStore((state) => state.state?.sheriffId);

  const [showSheriffAlert, setShowSheriffAlert] = useState(false);
  const [newSheriff, setNewSheriff] = useState<number | null>(null);
  const lastProcessedSheriffRef = useRef<number | null | undefined>(null);
  const sheriffTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (sheriffId === undefined || sheriffId === null) {
      return;
    }
    if (sheriffId === lastProcessedSheriffRef.current) {
      return;
    }

    if (sheriffTimeoutRef.current) {
      clearTimeout(sheriffTimeoutRef.current);
      sheriffTimeoutRef.current = null;
    }

    setNewSheriff(sheriffId);
    setShowSheriffAlert(true);
    lastProcessedSheriffRef.current = sheriffId;

    sheriffTimeoutRef.current = setTimeout(() => {
      setShowSheriffAlert(false);
      sheriffTimeoutRef.current = null;
    }, 3500);
  }, [sheriffId]);

  useEffect(() => {
    return () => {
      if (sheriffTimeoutRef.current) {
        clearTimeout(sheriffTimeoutRef.current);
      }
    };
  }, []);

  const isMurderAlert = phase === "DAY_ANNOUNCEMENT" && victimId !== null && victimId !== undefined;

  return (
    <>
      <AnimatePresence>
        {isMurderAlert && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="fixed inset-0 z-[120] pointer-events-none flex items-center justify-center p-6 bg-red-950/40 backdrop-blur-sm"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.8, y: 50 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 1.1 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent,_rgba(153,27,27,0.8))] mix-blend-overlay pointer-events-none"
            />

            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              exit={{ opacity: 0, scale: 0.8, y: -20 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="relative bg-zinc-950 border border-red-800 p-8 rounded shadow-[0_0_80px_rgba(220,38,38,0.6)] flex flex-col items-center justify-center select-none overflow-hidden"
            >
              <div className="absolute inset-0 bg-red-900/10 pointer-events-none bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(220,38,38,0.1)_2px,rgba(220,38,38,0.1)_4px)]" />
              <div className="absolute top-0 inset-x-0 h-1 bg-red-600 shadow-[0_0_10px_rgba(220,38,38,1)]" />
              <div className="absolute bottom-0 inset-x-0 h-1 bg-red-600 shadow-[0_0_10px_rgba(220,38,38,1)]" />

              <Skull className="w-16 h-16 text-red-500 animate-pulse mb-4 relative z-10" />

              <span className="font-serif text-red-500 text-sm tracking-[0.5em] uppercase mb-1 relative z-10 font-black">
                BLOOD MOON
              </span>
              <h1 className="font-sans font-black text-4xl text-red-100 tracking-wider mb-2 relative z-10 drop-shadow-[0_0_10px_rgba(220,38,38,0.8)]">
                【 {victimId} 号 】昨夜遇害
              </h1>
              <p className="font-mono text-zinc-400 text-xs tracking-widest relative z-10 mt-2 text-center">
                昨夜，死亡的阴影降临在这个座位。
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

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

              <span className="font-serif text-yellow-500 text-sm tracking-[0.5em] uppercase mb-1 relative z-10 font-bold">
                CROWNED HONOR
              </span>
              <h1 className="font-sans font-black text-4xl text-yellow-100 tracking-wider mb-2 relative z-10 drop-shadow-[0_0_10px_rgba(234,179,8,0.8)]">
                【 {newSheriff} 号 】当选警长
              </h1>
              <p className="font-mono text-zinc-300 text-base tracking-widest relative z-10 mt-3 font-bold bg-yellow-950/80 px-4 py-2 rounded border border-yellow-800/50">
                1.5 倍归票权已生效
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
