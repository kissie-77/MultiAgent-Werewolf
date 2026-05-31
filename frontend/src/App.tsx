import React, { useEffect, useState } from "react";
import ThreeCanvas from "./components/ThreeCanvas";
import CardDeck from "./components/CardDeck";
import SpeechConsole from "./components/SpeechConsole";
import ControlPanel from "./components/ControlPanel";
import TopHeader from "./components/TopHeader";
import GameSetup from "./components/GameSetup";
import GameOverPanel from "./components/GameOverPanel";
import { useGameStore } from "./store";
import { Skull, ShieldAlert } from "lucide-react";
import { motion } from "motion/react";

export default function App() {
  const fetchState = useGameStore((state) => state.fetchState);
  const gameState = useGameStore((state) => state.state);
  const resetGame = useGameStore((state) => state.resetGame);
  const exitGame = useGameStore((state) => state.exitGame);
  const [isSpeechExpanded, setIsSpeechExpanded] = useState(true);
  const [speechHeight, setSpeechHeight] = useState(210);
  const [isDragging, setIsDragging] = useState(false);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);

  // Initialize game state on page load
  useEffect(() => {
    fetchState();
  }, [fetchState]);

  if (!gameState) {
    return (
      <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-800 rounded-full animate-spin" />
        <span>召唤宿命之光...</span>
      </div>
    );
  }

  if (gameState.phase === "START_SCREEN") {
    return (
      <div className="relative w-screen h-screen flex flex-col items-center justify-center bg-[#0b0914] text-zinc-100 overflow-hidden font-sans select-none antialiased">
        {/* Cinematic orbiting 3D Roundtable background */}
        <ThreeCanvas />
        
        {/* Glassmorphic floating setup form */}
        <GameSetup />
        
        {/* Heavy woodcut border frame overlay */}
        <div className="absolute inset-0 pointer-events-none border-4 border-zinc-950/80 z-50 rounded" />
      </div>
    );
  }

  // Drag handler for panel resizing
  const startResizing = (mouseDownEvent: React.MouseEvent) => {
    mouseDownEvent.preventDefault();
    setIsDragging(true);
    const startY = mouseDownEvent.clientY;
    const startHeight = speechHeight;

    const doDrag = (mouseMoveEvent: MouseEvent) => {
      const deltaY = mouseMoveEvent.clientY - startY;
      const newHeight = Math.max(120, Math.min(window.innerHeight - 260, startHeight - deltaY));
      setSpeechHeight(newHeight);
      if (!isSpeechExpanded) {
        setIsSpeechExpanded(true);
      }
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
      const currentTouch = touchMoveEvent.touches[0];
      const deltaY = currentTouch.clientY - startY;
      const newHeight = Math.max(120, Math.min(window.innerHeight - 260, startHeight - deltaY));
      setSpeechHeight(newHeight);
      if (!isSpeechExpanded) {
        setIsSpeechExpanded(true);
      }
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
    <div className="relative w-screen h-screen flex flex-col bg-[#0b0914] text-zinc-100 overflow-hidden font-sans select-none antialiased">
      {/* 3D Render Studio Canvas Layer */}
      <ThreeCanvas />

      {/* GameOver Panel Overlay */}
      {gameState?.phase === "GAME_OVER" && (
        <GameOverPanel gameState={gameState} onRestart={resetGame} onExit={exitGame} />
      )}

      {/* 2D Overlay Interface */}
      <div className="absolute inset-0 flex flex-col pointer-events-none z-10 w-full h-full">
        
        {/* Top Header Deck (always interactive) */}
        <div className="pointer-events-auto">
          <TopHeader />
        </div>

        {/* Main Workspace Layout (split sidebar + transparent center scene) */}
        <div className="flex-grow flex flex-row w-full min-h-0 relative">
          
          {/* Left Panel Sidebar: Card Deck with glassmorphic transparency & collapsible motion */}
          <motion.div
            initial={{ width: 280 }}
            animate={{ width: isSidebarExpanded ? 280 : 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="pointer-events-auto shrink-0 border-r border-zinc-900/50 flex flex-col h-full overflow-hidden relative"
          >
            <CardDeck />
          </motion.div>

          {/* Sidebar Toggle Tab Button overlapping the edge */}
          <motion.button
            type="button"
            onClick={() => setIsSidebarExpanded(!isSidebarExpanded)}
            animate={{ left: isSidebarExpanded ? 280 : 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="pointer-events-auto absolute top-1/2 -translate-y-1/2 z-40 bg-zinc-950/90 hover:bg-yellow-500 hover:text-black border-y border-r border-zinc-800/80 text-zinc-300 w-5 h-14 rounded-r cursor-pointer flex items-center justify-center shadow-lg transition-colors"
          >
            <span className="text-[9px] font-bold">{isSidebarExpanded ? "◀" : "▶"}</span>
          </motion.button>

          {/* Right/Center Area: Floating transparent view above with combined bottom console panel */}
          <div className="flex-grow flex flex-col justify-between min-w-0 h-full relative">
            
            {/* Top Transparent Space for 3D Camera Focus & Gameplay */}
            <div className="flex-grow p-4 pointer-events-none flex items-start justify-end">
              {gameState?.winner && (
                <div className="bg-red-950/90 border-2 border-red-500/80 px-4 py-2.5 rounded shadow-2xl relative max-w-sm pointer-events-auto animate-bounce flex items-center gap-3">
                  <Skull className="w-6 h-6 text-red-500 shrink-0" />
                  <div className="flex flex-col">
                    <span className="font-sans font-black text-xs uppercase tracking-widest text-red-100">
                      审判庭决议：终盘
                    </span>
                    <span className="font-mono text-[9px] text-zinc-400 mt-0.5">
                      {gameState.winner === "WOLVES" ? "狼人肆虐 篡夺王庭" : "好人抱团 朝晖复苏"}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Console Panel (containing Speech Log + User Input/Skill Bar stacked) */}
            <div className="w-full flex flex-col pointer-events-auto bg-transparent border-t border-zinc-900/40 relative z-10 shrink-0">
              
              {/* Drag resizing handle with sleek styling */}
              <div 
                className="w-full h-2.5 bg-zinc-950/80 border-y border-zinc-900/50 hover:bg-yellow-500/80 cursor-ns-resize flex items-center justify-center gap-1.5 transition-colors select-none z-30"
                onMouseDown={startResizing}
                onTouchStart={startResizingTouch}
              >
                <div className="w-12 h-0.5 bg-zinc-700 rounded-full" />
                <div className="w-1 h-1 bg-zinc-700 rounded-full" />
                <div className="w-1 h-1 bg-zinc-700 rounded-full" />
              </div>

              {/* Speech Log Console (the log timeline scroll area) with dynamic height animation */}
              <motion.div
                initial={{ height: 210 }}
                animate={{ height: isSpeechExpanded ? speechHeight : 38 }}
                transition={isDragging ? { duration: 0 } : { type: "spring", stiffness: 320, damping: 28 }}
                className="flex flex-col min-h-0 border-b-2 border-zinc-900/50 overflow-hidden"
              >
                <SpeechConsole isExpanded={isSpeechExpanded} onToggle={() => setIsSpeechExpanded(!isSpeechExpanded)} />
              </motion.div>
              
              {/* User Input, Auto Debate & Skill Actions at the absolute bottom */}
              <ControlPanel />
            </div>

          </div>

        </div>

      </div>

      {/* Heavy woodcut frame outlines around the browser border */}
      <div className="absolute inset-0 pointer-events-none border-4 border-zinc-950/80 z-50 rounded" />
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-b from-[#a855f7]/30 to-transparent pointer-events-none z-50" />
      <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-r from-[#a855f7]/20 to-transparent pointer-events-none z-50" />
    </div>
  );
}
