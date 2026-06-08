import React from "react";
import { useGameStore } from "../store";
import { Player } from "../types";
import { motion, AnimatePresence } from "motion/react";
import { getRoleImage } from "../utils/roles";

// Black and White high-contrast woodcut-themed SVGs for each role illustration
function RoleIllustration({ roleColor, role, isExposed }: { roleColor: string; role: string; isExposed: boolean }) {
  // Hidden Identity Horizontal design
  return (
    <svg viewBox="0 0 160 100" className="w-full h-full text-zinc-400 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Woodcut frame border */}
      <rect x="5" y="5" width="150" height="90" rx="3" stroke="currentColor" strokeWidth="3" fill="none" />
      <rect x="8" y="8" width="144" height="84" rx="2" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" fill="none" />
      
      {/* Central mystical pattern (All-Seeing Eye) */}
      <path d="M80 30 L105 70 L55 70 Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="miter" />
      <circle cx="80" cy="55" r="12" stroke="currentColor" strokeWidth="3" />
      <line x1="80" y1="20" x2="80" y2="30" stroke="currentColor" strokeWidth="2" />
      <line x1="45" y1="85" x2="115" y2="85" stroke="currentColor" strokeWidth="2" />
      
      {/* Moon phases */}
      <circle cx="80" cy="15" r="5" fill="currentColor" />

      {/* Hand drawn scratch indicators */}
      <line x1="15" y1="15" x2="25" y2="25" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      <line x1="145" y1="85" x2="135" y2="75" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      <line x1="140" y1="20" x2="145" y2="15" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      
      {/* Label "? ? ?" */}
      <text x="80" y="58" fill="currentColor" fontSize="10" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="1" opacity="0.5">秘 匿</text>
    </svg>
  );
}

export default function CardDeck() {
  const gameState = useGameStore((state) => state.state);
  const selectedCardId = useGameStore((state) => state.selectedTargetSeat);
  const setSelectedCardId = useGameStore((state) => state.setSelectedTargetSeat);
  const pendingInput = useGameStore((state) => state.pendingInput);

  const players = gameState?.players || [];
  const currentSpeakerId = gameState?.currentSpeakerId;
  const phase = gameState?.phase;

  // Decide context colors
  const isNight = phase?.startsWith("NIGHT");

  // Clicking a player card sets the shared selection target — but only when an
  // input is pending and the seat is a valid target (mirrors SeatCommandDock + 3D board).
  const handleCardClick = (player: Player) => {
    if (!player.isAlive) return; // dead players don't spark action inputs
    const targets = pendingInput?.valid_targets ?? [];
    if (pendingInput && !targets.includes(player.id)) return;
    setSelectedCardId(selectedCardId === player.id ? null : player.id);
  };

  // Check if skills have been exhausted based on gameState
  const user = gameState?.players.find((p) => p.isUser);
  const isDead = user ? !user.isAlive : true;
  const userRole = user?.role || "村民";

  const isSeerSkillUsed = gameState?.seerVerifiedTarget !== null;
  const isWitchSaveUsed = gameState?.witchSaved;
  const isWitchPoisonUsed = gameState?.witchPoisonedTarget !== null;
  const isWolfBiteUsed = gameState?.wolfKilledTarget !== null;
  const victimId = gameState?.victimId;

  const [llmExposeAll, setLlmExposeAll] = React.useState(false);

  return (
    <div className="flex flex-col h-full w-[320px] bg-indigo-950/40 bg-woodcut backdrop-blur-md px-4 py-4 select-none relative z-10 shrink-0 shadow-2xl overflow-y-auto">
      
      {gameState?.gameMode === "llmOnly" && (
        <div className="flex items-center justify-between mb-4 border border-indigo-800/80 bg-slate-900/60 px-3 py-2 rounded-lg shadow-inner">
          <span className="text-[11px] font-sans font-bold text-indigo-300">全局上帝视角 👁️</span>
          <button 
            onClick={() => setLlmExposeAll(!llmExposeAll)}
            className={`w-9 h-5 rounded-full relative transition-colors shadow-inner ${llmExposeAll ? 'bg-blue-500' : 'bg-slate-700'}`}
          >
            <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform shadow ${llmExposeAll ? 'translate-x-4' : 'translate-x-0'}`} />
          </button>
        </div>
      )}

      {/* Grid of character illustration cards */}
      <div className="flex flex-col gap-3">
        <AnimatePresence>
          {players.map((p) => {
            const isSpeaking = currentSpeakerId === p.id;
            const isSelected = selectedCardId === p.id;
            
            // Identity exposure: expose if it is the User themselves, OR if they are dead, OR if game is over!
            // ...but only when we actually KNOW the role — a hidden seat (redacted role="") stays 秘匿.
            const isExposed = (p.isUser || !p.isAlive || phase === "GAME_OVER" || (gameState?.gameMode === "llmOnly" && llmExposeAll)) && !!p.role;

  
            // Color tags for role highlights
            let roleColor = "text-zinc-400";
            if (isExposed) {
              const WOLF_CAMP = ["狼人", "狼王", "白狼", "狼美人", "守卫狼", "隐狼", "血月使徒", "梦魇狼"];
              if (WOLF_CAMP.includes(p.role)) roleColor = "text-red-500 font-bold ink-shadow";
              else if (p.role === "预言家") roleColor = "text-[#c084fc] font-bold ink-shadow";
              else if (p.role === "女巫") roleColor = "text-[#eab308] font-bold ink-shadow";
              else if (p.role === "猎人") roleColor = "text-[#3b82f6] font-bold ink-shadow";
              else roleColor = "text-[#10b981] font-bold ink-shadow";
            }
  
            return (
              <motion.div
                layout
                initial={{ opacity: 0, scale: 0.9, y: 30 }}
                animate={{ 
                  opacity: !p.isAlive ? 0.45 : isSpeaking || isSelected ? 1 : 0.8, 
                  scale: isSelected ? 1.05 : isSpeaking ? 1.02 : 1, 
                  y: 0,
                  boxShadow: isSelected ? "0px 0px 20px rgba(255, 255, 255, 0.2)" : "none",
                  zIndex: isSelected || isSpeaking ? 10 : 1
                }}
                exit={{ opacity: 0, scale: 0.9, y: 30 }}
                whileHover={{ opacity: 1, scale: isSelected ? 1.05 : 1.02 }}
                transition={{ duration: 0.4, ease: "easeOut", layout: { type: "spring", stiffness: 300, damping: 30 } }}
                key={p.id}
                onClick={() => handleCardClick(p)}
                className={`group relative flex flex-col cursor-pointer rounded-lg overflow-hidden select-none transition-all duration-300 border shadow-lg ${
                  !p.isAlive
                    ? "border-[#1e1a18]/40 hover:cursor-not-allowed scale-95"
                    : isSpeaking
                      ? "border-yellow-400/80 ring-2 ring-yellow-400/40 shadow-[0_0_15px_rgba(250,204,21,0.3)]"
                      : isSelected
                        ? "border-zinc-200"
                        : "border-zinc-800 hover:border-zinc-500"
                }`}
              >
                {/* Card Main Image */}
                <div className="relative w-full aspect-[16/9] bg-zinc-950 overflow-hidden">
                  {isExposed ? (
                    <img src={getRoleImage(p.role)} alt={p.role} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full scale-105">
                       <RoleIllustration roleColor={roleColor} role={p.role} isExposed={false} />
                    </div>
                  )}
                  
                  {/* Overlay Gradient for readability */}
                  <div className="absolute inset-x-0 bottom-0 top-1/2 bg-gradient-to-t from-black/90 via-black/60 to-transparent pointer-events-none" />

                  {/* ID Badge overlay top-left */}
                  <div className={`absolute top-1 left-1 w-6 h-6 flex items-center justify-center rounded-full text-[12px] font-black shadow backdrop-blur-md border ${isSpeaking ? 'bg-yellow-500 text-black border-yellow-300' : 'bg-black/80 text-white border-zinc-500/50'}`}>
                     {p.id}
                  </div>

                  {/* Dead Overlay Banner */}
                  {!p.isAlive && (
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center backdrop-blur-[1px]">
                      <span className="text-[14px] text-red-650 font-extrabold tracking-widest border-2 border-red-700/80 px-2 py-1 uppercase bg-black/90 rotate-[15deg] shadow-[0_0_15px_rgba(220,38,38,0.5)] z-10">
                        放 逐
                      </span>
                    </div>
                  )}

                  {/* Animated Big Sheriff Badge */}
                  {gameState?.hasSheriff && gameState.sheriffId === p.id && (
                    <div className="absolute -top-1 right-2 w-10 h-14 z-20 pointer-events-none drop-shadow-[0_0_8px_rgba(234,179,8,0.8)] filter drop-shadow animate-pulse">
                        <svg viewBox="0 0 40 60" className="w-full h-full" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M20 2L35 12V35C35 45 28 53 20 58C12 53 5 45 5 35V12L20 2Z" fill="#854d0e" stroke="#facc15" strokeWidth="2.5" />
                          <circle cx="20" cy="25" r="9" fill="#1e1a18" stroke="#fef08a" strokeWidth="1.5" />
                          <path d="M20 18L22 23H27L23 26L24.5 31L20 28L15.5 31L17 26L13 23H18L20 18Z" fill="#facc15" />
                        </svg>
                    </div>
                  )}

                  {/* Speaking Badge */}
                  {isSpeaking && (
                     <div className="absolute top-1 left-8 bg-yellow-500 text-black text-[9px] font-black px-1.5 py-0.5 rounded shadow animate-pulse border border-yellow-300">言</div>
                  )}
                </div>

                {/* Player Metadata Deck - Footer Overlaid directly over bottom */}
                <div className="absolute bottom-0 left-0 right-0 p-2 flex flex-col pointer-events-none">
                  <div className="flex justify-between items-center gap-1 w-full relative z-20">
                     <h3 className={`font-sans font-black text-xs truncate drop-shadow-md flex-grow ${p.isUser ? "text-yellow-400" : "text-white"}`}>
                       {p.name}
                     </h3>
                     {p.isUser && (
                        <span className="text-[8px] bg-red-600 text-white px-1 py-0.5 rounded font-black shrink-0 shadow">你</span>
                     )}
                  </div>
                  <div className="flex flex-col mt-0.5 pointer-events-none">
                    <p className="font-mono text-[10px] uppercase font-bold drop-shadow truncate min-w-0 pointer-events-none">
                      <span className={roleColor}>{isExposed ? p.role : "未知秘匿"}</span>
                    </p>
                    {/* Status notes (Seer) */}
                    {p.statusNotes && (
                      <p className="font-mono text-[8.5px] text-fuchsia-300 mt-1 font-bold tracking-tight truncate pointer-events-none border-t border-fuchsia-500/30 pt-0.5">
                        {p.statusNotes}
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
