import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ThreeCanvas from "../components/ThreeCanvas";
import CardDeck from "../components/CardDeck";
import SpeechConsole from "../components/SpeechConsole";
import ControlPanel from "../components/ControlPanel";
import TopHeader from "../components/TopHeader";
import GameSetup from "../components/GameSetup";
import GameOverPanel from "../components/GameOverPanel";
import SpectatePanel from "../components/SpectatePanel";
import { useGameStore } from "../store";
import { Skull } from "lucide-react";
import { motion } from "motion/react";

export default function GamePage() {
  const fetchState = useGameStore((state) => state.fetchState);
  const gameState = useGameStore((state) => state.state);
  const resetGame = useGameStore((state) => state.resetGame);
  const exitGame = useGameStore((state) => state.exitGame);
  const [isSpeechExpanded, setIsSpeechExpanded] = useState(true);
  const [speechHeight, setSpeechHeight] = useState(210);
  const [isDragging, setIsDragging] = useState(false);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  if (!gameState) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-[#0d0907] font-mono text-xs uppercase tracking-widest text-zinc-400">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-800 border-t-yellow-500" />
        <span>召唤宿命之光...</span>
      </div>
    );
  }

  if (gameState.phase === "START_SCREEN") {
    return (
      <div className="relative flex h-screen w-screen select-none flex-col items-center justify-center overflow-hidden bg-[#0b0914] font-sans text-zinc-100 antialiased">
        <ThreeCanvas />
        <div className="pointer-events-auto relative z-10 flex w-full max-w-2xl flex-col items-center gap-4 px-4">
          <GameSetup />
          <SpectatePanel compact />
        </div>
        <Link
          to="/"
          className="pointer-events-auto absolute left-4 top-4 z-20 font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-200"
        >
          ← 返回启动页
        </Link>
        <div className="pointer-events-none absolute inset-0 z-50 rounded border-4 border-zinc-950/80" />
      </div>
    );
  }

  const startResizing = (mouseDownEvent: React.MouseEvent) => {
    mouseDownEvent.preventDefault();
    setIsDragging(true);
    const startY = mouseDownEvent.clientY;
    const startHeight = speechHeight;

    const doDrag = (mouseMoveEvent: MouseEvent) => {
      const deltaY = mouseMoveEvent.clientY - startY;
      const newHeight = Math.max(120, Math.min(window.innerHeight - 260, startHeight - deltaY));
      setSpeechHeight(newHeight);
      if (!isSpeechExpanded) setIsSpeechExpanded(true);
    };

    const stopDrag = () => {
      setIsDragging(false);
      window.removeEventListener("mousemove", doDrag);
      window.removeEventListener("mouseup", stopDrag);
    };

    window.addEventListener("mousemove", doDrag);
    window.addEventListener("mouseup", stopDrag);
  };

  const startResizingTouch = (touchStartEvent: React.TouchEvent) => {
    if (touchStartEvent.touches.length === 0) return;
    setIsDragging(true);
    const touch = touchStartEvent.touches[0];
    const startY = touch.clientY;
    const startHeight = speechHeight;

    const doDragTouch = (touchMoveEvent: TouchEvent) => {
      if (touchMoveEvent.touches.length === 0) return;
      const deltaY = touchMoveEvent.touches[0].clientY - startY;
      const newHeight = Math.max(120, Math.min(window.innerHeight - 260, startHeight - deltaY));
      setSpeechHeight(newHeight);
      if (!isSpeechExpanded) setIsSpeechExpanded(true);
    };

    const stopDragTouch = () => {
      setIsDragging(false);
      window.removeEventListener("touchmove", doDragTouch);
      window.removeEventListener("touchend", stopDragTouch);
    };

    window.addEventListener("touchmove", doDragTouch, { passive: true });
    window.addEventListener("touchend", stopDragTouch);
  };

  return (
    <div className="relative flex h-screen w-screen select-none flex-col overflow-hidden bg-[#0b0914] font-sans text-zinc-100 antialiased">
      <ThreeCanvas />

      {gameState.phase === "GAME_OVER" && (
        <GameOverPanel gameState={gameState} onRestart={resetGame} onExit={exitGame} />
      )}

      <div className="pointer-events-none absolute inset-0 z-10 flex h-full w-full flex-col">
        <div className="pointer-events-auto">
          <TopHeader />
        </div>

        <div className="relative flex min-h-0 w-full flex-grow flex-row">
          <motion.div
            initial={{ width: 280 }}
            animate={{ width: isSidebarExpanded ? 280 : 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="pointer-events-auto relative flex h-full shrink-0 flex-col overflow-hidden border-r border-zinc-900/50"
          >
            <CardDeck />
          </motion.div>

          <motion.button
            type="button"
            onClick={() => setIsSidebarExpanded(!isSidebarExpanded)}
            animate={{ left: isSidebarExpanded ? 280 : 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="pointer-events-auto absolute top-1/2 z-40 flex h-14 w-5 -translate-y-1/2 cursor-pointer items-center justify-center rounded-r border-y border-r border-zinc-800/80 bg-zinc-950/90 text-zinc-300 shadow-lg transition-colors hover:bg-yellow-500 hover:text-black"
          >
            <span className="text-[9px] font-bold">{isSidebarExpanded ? "◀" : "▶"}</span>
          </motion.button>

          <div className="relative flex h-full min-w-0 flex-grow flex-col justify-between">
            <div className="pointer-events-none flex flex-grow items-start justify-end p-4">
              {gameState.winner && (
                <div className="pointer-events-auto relative flex max-w-sm animate-bounce items-center gap-3 rounded border-2 border-red-500/80 bg-red-950/90 px-4 py-2.5 shadow-2xl">
                  <Skull className="h-6 w-6 shrink-0 text-red-500" />
                  <div className="flex flex-col">
                    <span className="font-sans text-xs font-black uppercase tracking-widest text-red-100">
                      审判庭决议：终盘
                    </span>
                    <span className="mt-0.5 font-mono text-[9px] text-zinc-400">
                      {gameState.winner === "WOLVES" ? "狼人肆虐 篡夺王庭" : "好人抱团 朝晖复苏"}
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="pointer-events-auto relative z-10 flex shrink-0 flex-col border-t border-zinc-900/40 bg-transparent">
              <div
                className="z-30 flex h-2.5 w-full cursor-ns-resize select-none items-center justify-center gap-1.5 border-y border-zinc-900/50 bg-zinc-950/80 transition-colors hover:bg-yellow-500/80"
                onMouseDown={startResizing}
                onTouchStart={startResizingTouch}
              >
                <div className="h-0.5 w-12 rounded-full bg-zinc-700" />
                <div className="h-1 w-1 rounded-full bg-zinc-700" />
                <div className="h-1 w-1 rounded-full bg-zinc-700" />
              </div>

              <motion.div
                initial={{ height: 210 }}
                animate={{ height: isSpeechExpanded ? speechHeight : 38 }}
                transition={isDragging ? { duration: 0 } : { type: "spring", stiffness: 320, damping: 28 }}
                className="flex min-h-0 flex-col overflow-hidden border-b-2 border-zinc-900/50"
              >
                <SpeechConsole
                  isExpanded={isSpeechExpanded}
                  onToggle={() => setIsSpeechExpanded(!isSpeechExpanded)}
                />
              </motion.div>

              <ControlPanel />
            </div>
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-0 z-50 rounded border-4 border-zinc-950/80" />
      <div className="pointer-events-none absolute inset-x-0 top-0 z-50 h-1 bg-gradient-to-b from-[#a855f7]/30 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 left-0 z-50 w-1 bg-gradient-to-r from-[#a855f7]/20 to-transparent" />
    </div>
  );
}
