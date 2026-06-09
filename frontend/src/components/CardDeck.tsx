import React from "react";
import { useGameStore } from "../store";
import { Player } from "../types";
import { motion, AnimatePresence } from "motion/react";
import { ChevronLeft, ChevronRight, Eye, EyeOff } from "lucide-react";
import { getRoleImage } from "../utils/roles";
import { soundManager } from "../audio/soundManager";

// Landscape woodcut "秘匿" placeholder for unknown identities. Matches the material
// art ratio (3:2) so hidden cards line up with revealed illustrations; the SVG fills
// (and may crop) its box — only hidden cards are allowed to crop, revealed art is not.
function RoleIllustration() {
  return (
    <svg viewBox="0 0 150 100" preserveAspectRatio="xMidYMid slice" className="w-full h-full text-zinc-400 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Woodcut frame border */}
      <rect x="5" y="5" width="140" height="90" rx="3" stroke="currentColor" strokeWidth="3" fill="none" />
      <rect x="8" y="8" width="134" height="84" rx="2" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" fill="none" />

      {/* Moon phase */}
      <circle cx="75" cy="22" r="5" fill="currentColor" />
      <line x1="75" y1="27" x2="75" y2="38" stroke="currentColor" strokeWidth="2" />

      {/* Central mystical pattern (All-Seeing Eye) */}
      <path d="M75 38 L100 72 L50 72 Z" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="miter" />
      <circle cx="75" cy="58" r="11" stroke="currentColor" strokeWidth="3" />
      <line x1="45" y1="80" x2="105" y2="80" stroke="currentColor" strokeWidth="2" />

      {/* Hand drawn scratch indicators */}
      <line x1="15" y1="15" x2="25" y2="25" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      <line x1="135" y1="85" x2="125" y2="75" stroke="currentColor" strokeWidth="1" opacity="0.3" />

      {/* Label "秘 匿" */}
      <text x="75" y="61" fill="currentColor" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="2" opacity="0.55">秘 匿</text>
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

  // Clicking a player card sets the shared selection target — but only when an
  // input is pending and the seat is a valid target (mirrors SeatCommandDock + 3D board).
  const handleCardClick = (player: Player) => {
    if (!player.isAlive) return; // dead players don't spark action inputs
    const targets = pendingInput?.valid_targets ?? [];
    if (pendingInput && !targets.includes(player.id)) return;
    soundManager.playUi("ui_click");
    setSelectedCardId(selectedCardId === player.id ? null : player.id);
  };

  // Spectator = god view (no human seat). gameState.gameMode is unreliable for this —
  // the live reducer defaults it to "llmOnly" for every run — so key off humanSeat,
  // the same signal LiveCueAnchors uses. A seated human never gets the reveal-all
  // toggle (would be cheating); spectate reveals everyone by default.
  const humanSeat = useGameStore((s) => s.humanSeat);
  const isSpectator = humanSeat == null;

  const [llmExposeAll, setLlmExposeAll] = React.useState(true);

  // Collapse to the left, leaving a slim re-open handle. Local state persists for
  // the whole match (CardDeck stays mounted); a new game remounts and resets it.
  const [collapsed, setCollapsed] = React.useState(false);

  return (
    <div className="relative h-full shrink-0 z-10 hidden md:flex pointer-events-auto">
      {/* Sliding panel — width animates to 0 when collapsed, content clipped */}
      <motion.div
        initial={false}
        animate={{ width: collapsed ? 0 : 312 }}
        transition={{ type: "spring", stiffness: 320, damping: 36 }}
        className="h-full overflow-hidden"
      >
        <div className="flex flex-col h-full w-[312px] bg-indigo-950/40 bg-woodcut backdrop-blur-md px-4 py-4 select-none shadow-2xl overflow-y-auto">

          {isSpectator && (
            <div className="flex justify-end mb-4 shrink-0">
              <button
                type="button"
                onClick={() => { soundManager.playUi("ui_click"); setLlmExposeAll(!llmExposeAll); }}
                title="全局上帝视角"
                aria-label="全局上帝视角"
                aria-pressed={llmExposeAll}
                className={`flex items-center justify-center w-9 h-9 rounded-md border bg-slate-950/70 bg-woodcut-dark backdrop-blur shadow-[inset_0_1px_2px_rgba(255,255,255,0.06),2px_2px_0_rgba(0,0,0,0.5)] transition-colors cursor-pointer ${
                  llmExposeAll
                    ? "border-amber-500/60 text-amber-300 hover:text-amber-100 hover:border-amber-400"
                    : "border-slate-700/70 text-slate-500 hover:text-slate-300 hover:border-slate-500"
                }`}
              >
                {llmExposeAll ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              </button>
            </div>
          )}

          {/* Stack of character illustration cards (native aspect ratio, no crop) */}
          <div className="flex flex-col gap-3">
            <AnimatePresence>
              {players.map((p) => {
                const isSpeaking = currentSpeakerId === p.id;
                const isSelected = selectedCardId === p.id;

                // Identity exposure: expose if it is the User themselves, OR if they are dead, OR if game is over,
                // OR (spectate only) when the god-view toggle is on. A redacted seat (role="") stays 秘匿.
                const isExposed = (p.isUser || !p.isAlive || phase === "GAME_OVER" || (isSpectator && llmExposeAll)) && !!p.role;

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
                    {/* Card Main Image — revealed shows full material art at native ratio; hidden uses portrait 秘匿 */}
                    <div className="relative w-full bg-zinc-950 overflow-hidden">
                      {isExposed ? (
                        <img src={getRoleImage(p.role)} alt={p.role} className="w-full h-auto block" />
                      ) : (
                        <div className="w-full aspect-[3/2]">
                          <RoleIllustration />
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
      </motion.div>

      {/* Collapse / re-open handle — sits on the panel's right edge; slides to the
          screen edge when the panel collapses to 0 width. */}
      <button
        type="button"
        onClick={() => { soundManager.playUi("ui_click"); setCollapsed((c) => !c); }}
        title={collapsed ? "展开座位名册" : "收起座位名册"}
        aria-label={collapsed ? "展开座位名册" : "收起座位名册"}
        className="self-center shrink-0 h-24 w-6 flex items-center justify-center bg-slate-950/90 bg-woodcut-dark border border-l-0 border-amber-700/50 rounded-r-md text-amber-300/80 hover:text-amber-100 hover:border-amber-500/70 shadow-[2px_0_12px_rgba(0,0,0,0.5)] transition-colors cursor-pointer z-30"
      >
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </div>
  );
}
