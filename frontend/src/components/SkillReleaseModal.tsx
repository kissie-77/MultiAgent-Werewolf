import React, { useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import { useGameStore } from "../store";
import { getTarotImage } from "../utils/roles";

interface Player {
  id: number;
  name: string;
  isAlive: boolean;
  role: string | null;
}

interface SkillReleaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  actionName: string;
  actionIcon: string;
  actionPrefix?: string;
  actionPrompt?: string;
  eligiblePlayers: Player[];
  onConfirm: (targetId: number) => void;
  userRole: string;
}

export const SkillReleaseModal = ({
  isOpen,
  onClose,
  actionName,
  actionIcon,
  actionPrefix = "释放技能",
  actionPrompt = "请在下方序列选取您的目标：",
  eligiblePlayers,
  onConfirm,
  userRole
}: SkillReleaseModalProps) => {
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);

  // Per-role tarot card for the skill overlay (all 22 roles, English + Chinese).
  const imageSrc = getTarotImage(userRole);

  const handleSelect = (id: number) => {
    setSelectedCardId(id);
  };

  const handleConfirm = () => {
    if (selectedCardId) {
      onConfirm(selectedCardId);
      // Wait a moment then close
      setTimeout(() => {
        onClose();
        setSelectedCardId(null);
      }, 300);
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[200] flex flex-col items-center justify-center p-4 bg-black/80 backdrop-blur-md pointer-events-auto overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: -10 }}
        className="flex flex-col items-center relative w-full max-w-xl !overflow-visible my-auto"
      >
        <button
          onClick={onClose}
          className="absolute -top-6 right-0 md:-right-6 text-amber-900/60 hover:text-amber-500 transition-colors z-[110] hover:rotate-90 duration-300"
        >
          <X className="w-8 h-8" />
        </button>

        {/* Full Tarot Card Image */}
        <div className="w-[180px] h-[306px] sm:w-[220px] sm:h-[374px] relative rounded-lg shadow-[0_0_60px_rgba(245,158,11,0.2)] flex flex-col items-center justify-center overflow-hidden z-20 mb-4 border border-amber-900/50 flex-shrink-0">
            <img 
              src={imageSrc}
              alt={userRole}
              className="w-full h-full object-cover object-center filter contrast-[1.1] saturate-75"
            />
            {/* Subtle overlay glare */}
            <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent pointer-events-none" />
        </div>

        <div className="text-center mb-4 relative z-20 flex-shrink-0">
           <div className="flex items-center justify-center gap-2 mb-1.5 opacity-80">
             <div className="w-1 h-1 bg-amber-500/60 rotate-45" />
             <span className="font-serif text-[9px] uppercase tracking-[0.25em] text-amber-500/80">
               ARCANA DECISION
             </span>
             <div className="w-1 h-1 bg-amber-500/60 rotate-45" />
           </div>
           
           <h2 className="font-serif text-2xl lg:text-3xl font-medium text-transparent bg-clip-text bg-gradient-to-b from-amber-100 via-amber-300 to-amber-700 tracking-[0.1em] drop-shadow-md mb-1">
             [ {actionPrefix} : {actionName} ]
           </h2>
          <span className="text-[10px] text-amber-900/60 font-mono tracking-widest">{actionPrompt}</span>
        </div>

        {/* Targets */}
        <div className="flex flex-wrap items-center justify-center gap-3 w-full mb-6 relative z-20 flex-shrink-0">
          {eligiblePlayers.length === 0 ? (
            <span className="text-amber-900/50 text-sm font-serif italic py-4 tracking-[0.2em]">— 没有可用灵魂 —</span>
          ) : (
            eligiblePlayers.map((p) => {
              const isSelected = p.id === selectedCardId;
              return (
                <button
                  key={p.id}
                  onClick={() => handleSelect(p.id)}
                  className={`flex flex-col items-center justify-center w-[64px] h-[86px] rounded transition-all duration-300 cursor-pointer font-serif border-2 overflow-hidden relative group transform-gpu ${
                    isSelected 
                      ? "bg-amber-600/20 text-white border-amber-500/80 shadow-[0_0_15px_rgba(245,158,11,0.4)] scale-105" 
                      : "bg-[#0c0808] border-amber-900/30 text-amber-700/60 hover:border-amber-600/50 hover:bg-[#150d0d] hover:-translate-y-1 hover:shadow-lg hover:text-amber-500"
                  }`}
                >
                  <div className="absolute inset-0 bg-woodcut-dark opacity-30 group-hover:opacity-40 transition-opacity" />
                  <span className={`text-xl font-black leading-none mb-1 relative z-10 ${isSelected ? "drop-shadow-md text-amber-100" : ""}`}>
                    {p.id}
                  </span>
                  <span className={`text-[8px] truncate max-w-[50px] tracking-widest relative z-10 ${isSelected ? "text-amber-200" : "opacity-60"}`}>{p.name}</span>
                  {isSelected && (
                     <div className="absolute bottom-0 w-full h-1 bg-amber-500/80" />
                  )}
                </button>
              );
            })
          )}
        </div>

        <div className="w-full flex justify-center relative z-20 flex-shrink-0 pb-4">
          <button
            onClick={handleConfirm}
            disabled={!selectedCardId}
            className={`relative px-12 py-3.5 font-black font-serif text-xs tracking-[0.3em] uppercase rounded transition-all duration-300 flex items-center justify-center overflow-hidden border ${
              !selectedCardId
                ? "bg-[#0c0808] text-amber-900/30 cursor-not-allowed border-amber-900/20"
                : "bg-gradient-to-r from-[#201008] via-[#3a1d0f] to-[#201008] text-amber-500 border-amber-500/50 hover:scale-105 hover:shadow-[0_0_20px_rgba(245,158,11,0.3)] shadow-lg hover:text-amber-300 active:scale-95 cursor-pointer"
            }`}
          >
            <div className="absolute inset-0 bg-woodcut pointer-events-none opacity-20" />
            <span className="relative z-10 flex items-center gap-2">确 认 执 行</span>
          </button>
        </div>
      </motion.div>
    </div>,
    document.body
  );
};
