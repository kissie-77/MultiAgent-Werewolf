import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useGameInsight } from "../hooks/useGameInsight";
import { useGameStore } from "../store";
import BeliefMatrixPanel from "./BeliefMatrixPanel";
import ExposureRadarStrip from "./ExposureRadarStrip";
import VoteIntentionPanel from "./VoteIntentionPanel";
import WolfExposurePanel from "./WolfExposurePanel";
import { clampDockWidth } from "../lib/dockWidth";
import { Eye, EyeOff, Loader2 } from "lucide-react";

export default function InsightDock({ runId }: { runId: string | null }) {
  const { beliefs, voteSnapshot, players, speakerSeat } = useGameInsight(runId);
  const gameState = useGameStore(state => state.state);
  const [isExpanded, setIsExpanded] = useState(true);
  const [showIdentities, setShowIdentities] = useState(true);

  if (!beliefs || !voteSnapshot) {
    return (
      <div className="pointer-events-auto shrink-0 border border-t-0 border-amber-900/40 shadow-[0_4px_24px_rgba(0,0,0,0.8)] overflow-hidden bg-[#0c0a09]/95 hidden md:flex flex-col z-40 rounded-b-xl absolute right-6 top-12"
        style={{ width: '320px', maxHeight: 'calc(100vh - 4rem)' }}
      >
        <div className="text-amber-500 font-serif font-black text-sm uppercase tracking-widest px-3 py-2 flex items-center justify-between border-b border-amber-900/50 h-[2.5rem] shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[14px]">👁</span> 观战读心
          </div>
          <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-500/60" />
        </div>
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-zinc-500">
          <Loader2 className="w-5 h-5 animate-spin text-amber-500/40" />
          <span className="text-[10px] font-sans">洞察加载中...</span>
        </div>
      </div>
    );
  }

  const roundLabel = beliefs.length > 0 ? `R${beliefs[0].round}·昼` : "-";
  const isLLMOnly = gameState?.gameMode === "llmOnly";
  const canShowIdentities = isLLMOnly && showIdentities;

  const [width, setWidth] = useState(320);
  const resizeRef = useRef<{ startX: number; startWidth: number } | null>(null);

  const onResizeDown = (e: React.PointerEvent) => {
    e.stopPropagation(); // 阻止 framer-motion 的「拖拽移动面板」
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    resizeRef.current = { startX: e.clientX, startWidth: width };
  };
  const onResizeMove = (e: React.PointerEvent) => {
    if (!resizeRef.current) return;
    const { startX, startWidth } = resizeRef.current;
    // 面板右锚定：向左拖（clientX 变小）→ 变宽
    setWidth(clampDockWidth(startWidth + (startX - e.clientX), window.innerWidth));
  };
  const onResizeUp = (e: React.PointerEvent) => {
    resizeRef.current = null;
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
  };

  return (
    <>
      {/* Desktop Down-Accordion Panel */}
      <motion.div
        drag
        dragMomentum={false}
        className="pointer-events-auto shrink-0 border border-t-0 border-amber-900/40 shadow-[0_4px_24px_rgba(0,0,0,0.8)] overflow-hidden relative bg-[#0c0a09]/95 hidden md:flex flex-col z-40 transition-[max-height] duration-500 ease-in-out rounded-b-xl absolute right-6 top-12"
        style={{
          width: `${width}px`,
          maxHeight: isExpanded ? 'calc(100vh - 4rem)' : '2.5rem'
        }}
      >
        {isExpanded && (
          <div
            onPointerDown={onResizeDown}
            onPointerMove={onResizeMove}
            onPointerUp={onResizeUp}
            className="absolute left-0 top-0 h-full w-1.5 z-30 cursor-ew-resize bg-amber-500/0 hover:bg-amber-500/40 transition-colors"
            title="拖拽调整宽度"
          />
        )}

        {/* Subtle gothic border styling inside */}
        <div className="absolute inset-0 pointer-events-none border border-amber-500/10 m-1 rounded-b-lg"></div>

        {/* Accordion Toggle Header */}
        <div 
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-amber-500 font-serif font-black text-sm uppercase tracking-widest px-3 py-2 flex items-center justify-between border-b border-amber-900/50 drop-shadow cursor-grab active:cursor-grabbing hover:bg-black/40 transition-colors z-20 h-[2.5rem] shrink-0"
        >
           <div className="flex items-center gap-2 relative">
             <span className="text-[14px]">👁</span> 观战读心
             
             {/* Sub-toggle for identities without triggering parent click */}
             {isLLMOnly && (
               <button 
                 onClick={(e) => { e.stopPropagation(); setShowIdentities(!showIdentities); }}
                 className="flex items-center ml-2 px-1.5 py-0.5 rounded border border-amber-900/50 hover:bg-amber-900/30 text-amber-500/80 hover:text-amber-400 focus:outline-none transition-colors"
                 title={showIdentities ? "隐藏身份 (Hide Identities)" : "显示身份 (Show Identities)"}
               >
                 {showIdentities ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
               </button>
             )}
           </div>
           
           <div className="flex items-center justify-center p-1 rounded hover:bg-amber-900/30 text-amber-500/70 hover:text-amber-400 transition-colors">
             <span className="text-[10px] mr-1 font-sans">{isExpanded ? "收起" : "展开"}</span>
             <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-500 ${isExpanded ? '' : 'rotate-180'}`}>
                <path d="m18 15-6-6-6 6"/>
             </svg>
           </div>
        </div>

        <div className={`w-full flex flex-col flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-3 custom-scrollbar z-10 relative transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
          
          <BeliefMatrixPanel
            beliefs={beliefs}
            players={players}
            roundLabel={roundLabel}
            scope="god"
            showIdentities={canShowIdentities}
            currentSpeakerSeat={speakerSeat}
          />

          <ExposureRadarStrip beliefs={beliefs} speakerSeat={speakerSeat} />

          <VoteIntentionPanel
            snapshot={voteSnapshot}
            players={players}
            showIdentities={canShowIdentities}
          />

          {canShowIdentities && <WolfExposurePanel beliefs={beliefs} players={players} />}
        </div>
      </motion.div>

      {/* Mobile Bottom Drawer Toggle (Always visible button on mobile) */}
      <div className="md:hidden absolute top-[70%] right-0 pointer-events-auto z-40">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="bg-zinc-950 border-y border-l border-amber-900/60 text-amber-500 w-8 h-12 rounded-l cursor-pointer flex items-center justify-center shadow-[-4px_0_15px_rgba(0,0,0,0.8)]"
        >
           <span className="text-xs font-bold">👁</span>
        </button>
      </div>

      {/* Mobile Bottom Drawer overlay */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="md:hidden absolute bottom-0 left-0 right-0 h-[60%] bg-[#0c0a09]/95 border-t border-amber-900/60 shadow-[0_-10px_40px_rgba(0,0,0,0.9)] z-50 pointer-events-auto flex flex-col rounded-t-xl"
          >
            <div className="w-full flex justify-center py-2 shrink-0">
               <div className="w-12 h-1 bg-amber-900/50 rounded-full" />
            </div>
            
            <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-6 mt-2 space-y-4">
              <div className="text-amber-500 font-serif text-sm font-black uppercase flex items-center justify-between mb-2 drop-shadow">
                 <div className="flex items-center gap-2">
                   <span className="text-lg">👁</span> 观战读心 (Live)
                 </div>
                 {isLLMOnly && (
                   <button 
                     onClick={() => setShowIdentities(!showIdentities)}
                     className="flex items-center gap-1.5 px-2 py-1 rounded border border-amber-900/50 hover:bg-amber-900/30 text-amber-400 text-[10px] uppercase font-sans tracking-widest transition-colors cursor-pointer"
                   >
                     {showIdentities ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                   </button>
                 )}
              </div>
              
              <BeliefMatrixPanel
                beliefs={beliefs}
                players={players}
                roundLabel={roundLabel}
                scope="god"
                showIdentities={canShowIdentities}
                currentSpeakerSeat={speakerSeat}
              />

              <ExposureRadarStrip beliefs={beliefs} speakerSeat={speakerSeat} />

              <VoteIntentionPanel
                snapshot={voteSnapshot}
                players={players}
                showIdentities={canShowIdentities}
              />

              {canShowIdentities && <WolfExposurePanel beliefs={beliefs} players={players} />}
            </div>
            
            {/* Close button for mobile */}
            <button 
              onClick={() => setIsExpanded(false)}
              className="absolute top-3 right-4 w-8 h-8 flex items-center justify-center bg-zinc-900 border border-amber-900/50 rounded-full text-amber-500 cursor-pointer"
            >
              ✕
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
