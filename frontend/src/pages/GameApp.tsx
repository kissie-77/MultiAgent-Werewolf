import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ThreeCanvas from "../components/ThreeCanvas";
import CardDeck from "../components/CardDeck";
import SpeechConsole from "../components/SpeechConsole";
import ControlPanel from "../components/ControlPanel";
import TopHeader from "../components/TopHeader";
import GameSetup from "../components/GameSetup";
import GameOverPanel from "../components/GameOverPanel";
import InsightDock from "../components/InsightDock";
import { useGameStore } from "../store";
import { Skull, ShieldAlert, ArrowLeft } from "lucide-react";
import { motion } from "motion/react";
import CastSkillOverlay from "../components/CastSkillOverlay";
import AlertOverlays from "../components/AlertOverlays";

export default function GameApp() {
  const fetchState = useGameStore((state) => state.fetchState);
  const gameState = useGameStore((state) => state.state);
  const resetGame = useGameStore((state) => state.resetGame);
  const exitGame = useGameStore((state) => state.exitGame);
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
      <div className="relative w-screen h-screen flex flex-col items-center justify-center bg-gradient-to-br from-indigo-950 via-slate-900 to-blue-950 text-slate-100 overflow-hidden font-sans select-none antialiased">
        <div className="absolute inset-0 bg-woodcut-dark opacity-30 mix-blend-multiply pointer-events-none z-0" />
        {/* Cinematic orbiting 3D Roundtable background */}
        <ThreeCanvas />
        
        {/* Glassmorphic floating setup form */}
        <GameSetup />
        
        {/* Heavy woodcut border frame overlay */}
        <div className="absolute inset-0 pointer-events-none border-4 border-indigo-900/40 shadow-[inset_0_0_100px_rgba(30,58,138,0.5)] z-50 rounded-xl" />
      </div>
    );
  }

  const handleExitGame = async () => {
    await exitGame();
  };

  const isNight = gameState?.phase?.startsWith("NIGHT") || false;

  return (
    <div className={`relative w-screen h-screen flex flex-col transition-colors duration-[2000ms] ease-in-out ${isNight ? "bg-gradient-to-br from-[#0d0415] via-slate-900 to-[#1a0b2e] shadow-[inset_0_0_120px_rgba(76,29,149,0.4)]" : "bg-gradient-to-br from-amber-950 via-[#27150a] to-[#3f1905] shadow-[inset_0_0_120px_rgba(217,119,6,0.2)]"} text-slate-100 overflow-hidden font-sans select-none antialiased`}>
      <div className="absolute inset-0 bg-woodcut-dark opacity-30 mix-blend-multiply pointer-events-none z-0" />
      {/* 3D Render Studio Canvas Layer */}
      <ThreeCanvas />

      {/* GameOver Panel Overlay */}
      {gameState?.phase === "GAME_OVER" && (
        <GameOverPanel gameState={gameState} onRestart={resetGame} onExit={handleExitGame} />
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
            initial={{ width: 320 }}
            animate={{ width: isSidebarExpanded ? 320 : 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="pointer-events-auto shrink-0 border-r border-indigo-500/20 shadow-[4px_0_24px_rgba(0,0,0,0.5)] flex flex-col h-full overflow-hidden relative bg-[#09060c]/95"
          >
            <CardDeck />
          </motion.div>

          {/* Sidebar Toggle Tab Button overlapping the edge */}
          <motion.button
            type="button"
            onClick={() => setIsSidebarExpanded(!isSidebarExpanded)}
            animate={{ left: isSidebarExpanded ? 320 : 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="pointer-events-auto absolute top-1/2 -translate-y-1/2 z-40 bg-zinc-950 border border-amber-900/60 text-amber-500 hover:text-amber-400 hover:bg-zinc-900 hover:border-amber-700/80 w-6 h-24 rounded-r-md flex flex-col items-center justify-center shadow-[4px_0_20px_rgba(0,0,0,0.8)] transition-all group"
          >
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(245,158,11,0.15),_transparent)] pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-r-md"></div>
            <span className="font-serif text-[10px] text-amber-700 group-hover:text-amber-500 transition-colors mb-1">✦</span>
            <span className="font-mono text-[10px] font-black text-amber-600 group-hover:text-amber-400 transition-colors drop-shadow">{isSidebarExpanded ? "◀" : "▶"}</span>
            <span className="font-serif text-[10px] text-amber-700 group-hover:text-amber-500 transition-colors mt-1">✦</span>
          </motion.button>

          {/* Right/Center Area: Full-screen Speech Records Chronicle with ControlPanel at the bottom */}
          <div className="flex-grow flex flex-col min-w-0 h-full relative pointer-events-auto bg-transparent">
            
            {/* Full-screen Speech Log Console */}
            <div className="flex-grow flex flex-col min-h-0 overflow-hidden relative">
              
              {/* If winner exists, show small floating absolute badge above speech cards */}
              {gameState?.winner && (
                <div className="absolute top-4 right-4 z-30 bg-rose-950/90 border-2 border-rose-500/80 px-4 py-2.5 rounded shadow-2xl animate-bounce flex items-center gap-3">
                  <Skull className="w-6 h-6 text-rose-500 shrink-0" />
                  <div className="flex flex-col">
                    <span className="font-sans font-black text-xs uppercase tracking-widest text-rose-100">
                      审判庭决议：终盘
                    </span>
                    <span className="font-mono text-[9px] text-slate-300 mt-0.5">
                      {gameState.winner === "WOLVES" ? "狼人肆虐 篡夺王庭" : "好人抱团 朝晖复苏"}
                    </span>
                  </div>
                </div>
              )}

              <SpeechConsole />
            </div>

            {/* User Input, Auto Debate & Actions at the bottom */}
            <div className="shrink-0 bg-transparent">
              <ControlPanel />
            </div>

          </div>

          <InsightDock runId={null} />
        </div>

      </div>

      {/* Frame outlines around the browser border */}
      <div className={`absolute inset-0 pointer-events-none border-[6px] z-50 rounded-2xl transition-colors duration-[2000ms] ${isNight ? "border-indigo-900/40 shadow-[inset_0_0_50px_rgba(0,0,0,0.8)]" : "border-amber-900/40 shadow-[inset_0_0_60px_rgba(30,10,0,0.8)]"}`} />
      <div className={`absolute inset-x-0 top-0 h-2 bg-gradient-to-b pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#3b82f6]/40" : "from-[#f59e0b]/40"} to-transparent`} />
      <div className={`absolute inset-y-0 left-0 w-2 bg-gradient-to-r pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#8b5cf6]/30" : "from-[#d97706]/30"} to-transparent`} />
      <div className={`absolute inset-y-0 right-0 w-2 bg-gradient-to-l pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#8b5cf6]/30" : "from-[#d97706]/30"} to-transparent`} />
      <div className={`absolute inset-x-0 bottom-0 h-2 bg-gradient-to-t pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#3b82f6]/40" : "from-[#f59e0b]/40"} to-transparent`} />

      {/* Cinematic & Event Alerts */}
      <AlertOverlays />

      {/* Interactive & Cinematic Skill Casting Overlay */}
      <CastSkillOverlay />
    </div>
  );
}
