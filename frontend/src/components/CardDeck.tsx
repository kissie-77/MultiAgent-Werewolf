import React from "react";
import { useGameStore } from "../store";

// Black and White high-contrast woodcut-themed SVGs for each role illustration
function RoleIllustration({ roleColor, role, isExposed }: { roleColor: string; role: string; isExposed: boolean }) {
  if (!isExposed) {
    // Hidden Identity Tarot card design
    return (
      <svg viewBox="0 0 120 160" className="w-full h-full text-zinc-400 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Woodcut frame border */}
        <rect x="5" y="5" width="110" height="150" rx="3" stroke="currentColor" strokeWidth="3" fill="none" />
        <rect x="8" y="8" width="104" height="144" rx="2" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" fill="none" />

        {/* Central mystical pattern (All-Seeing Eye) */}
        <path d="M60 45 L95 100 L25 100 Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="miter" />
        <circle cx="60" cy="85" r="15" stroke="currentColor" strokeWidth="3" />
        <line x1="60" y1="35" x2="60" y2="45" stroke="currentColor" strokeWidth="2" />
        <line x1="25" y1="120" x2="95" y2="120" stroke="currentColor" strokeWidth="2" />

        {/* Moon phases */}
        <circle cx="60" cy="22" r="6" fill="currentColor" />
        <path d="M30 22 Q40 12 30 2" stroke="currentColor" strokeWidth="1" />
        <path d="M90 22 Q80 12 90 2" stroke="currentColor" strokeWidth="1" />

        {/* Hand drawn scratch indicators */}
        <line x1="15" y1="15" x2="25" y2="25" stroke="currentColor" strokeWidth="1" opacity="0.3" />
        <line x1="105" y1="145" x2="95" y2="135" stroke="currentColor" strokeWidth="1" opacity="0.3" />
        <line x1="100" y1="20" x2="105" y2="15" stroke="currentColor" strokeWidth="1" opacity="0.3" />

        {/* Label "? ? ?" */}
        <text x="60" y="140" fill="currentColor" fontSize="12" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="2">秘 匿</text>
      </svg>
    );
  }

  // Draw specific stylized woodcut illustrations with dark high contrast and key color highlights
  switch (role) {
    case "预言家":
      return (
        <svg viewBox="0 0 120 160" className="w-full h-full text-zinc-100 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="5" width="110" height="150" rx="3" stroke="#a855f7" strokeWidth="3" />
          {/* Hooded Mage Silhouette */}
          <path d="M60 25 C45 25 35 40 35 55 C35 65 42 70 42 70 L30 115 L90 115 L78 70 C78 70 85 65 85 55 C85 40 75 25 60 25 Z" fill="#18181b" stroke="currentColor" strokeWidth="2.5" />
          {/* Eyes inside hood */}
          <circle cx="53" cy="45" r="2" fill="#a855f7" />
          <circle cx="67" cy="45" r="2" fill="#a855f7" />
          {/* Crystal Ball with neon violet glow */}
          <circle cx="60" cy="100" r="14" fill="#581c87" stroke="#c084fc" strokeWidth="2" />
          <path d="M52 95 Q60 85 68 95" stroke="#ffffff" strokeWidth="1.5" />
          <circle cx="57" cy="97" r="2" fill="#ffffff" />
          {/* Engraving lines */}
          <line x1="15" y1="135" x2="105" y2="135" stroke="currentColor" strokeWidth="2" />
          <line x1="30" y1="140" x2="90" y2="140" stroke="currentColor" strokeWidth="1" strokeDasharray="2 2" />
          <text x="60" y="150" fill="#c084fc" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">预言家 (SEER)</text>
        </svg>
      );
    case "女巫":
      return (
        <svg viewBox="0 0 120 160" className="w-full h-full text-zinc-100 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="5" width="110" height="150" rx="3" stroke="#eab308" strokeWidth="3" />
          {/* Witch Hat & Hair */}
          <path d="M25 50 L60 15 L95 50 Z" fill="#18181b" stroke="currentColor" strokeWidth="2" />
          <path d="M15 50 Q60 42 105 50 Q60 58 15 50" fill="#27272a" stroke="currentColor" strokeWidth="2" />
          <path d="M35 55 C25 70 30 110 30 110 L90 110 C90 110 95 70 85 55 Z" fill="#09090b" stroke="currentColor" strokeWidth="1.5" />
          {/* Poison bottle & Healing potion */}
          <rect x="42" y="80" width="12" height="18" rx="2" fill="#166534" stroke="#22c55e" strokeWidth="2" />
          <rect x="66" y="80" width="12" height="18" rx="2" fill="#7f1d1d" stroke="#f43f5e" strokeWidth="2" />
          <circle cx="48" cy="85" r="2" fill="#4ade80" />
          <circle cx="72" cy="85" r="2" fill="#fda4af" />
          {/* Liquid bubbles */}
          <circle cx="45" cy="74" r="1.5" fill="#22c55e" />
          <circle cx="74" cy="73" r="1.5" fill="#f43f5e" />
          <text x="60" y="150" fill="#eab308" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">女巫 (WITCH)</text>
        </svg>
      );
    case "猎人":
      return (
        <svg viewBox="0 0 120 160" className="w-full h-full text-zinc-100 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="5" width="110" height="150" rx="3" stroke="#2563eb" strokeWidth="3" />
          {/* Hunting cap and scowl face */}
          <path d="M30 45 Q60 30 90 45 L85 75 L35 75 Z" fill="#27272a" stroke="currentColor" strokeWidth="2" />
          {/* Feathers on cap */}
          <path d="M85 45 C95 30 100 20 95 15 C90 20 85 30 85 45 Z" fill="#3b82f6" stroke="currentColor" strokeWidth="1" />
          {/* Musket Rifle body with metal sheen */}
          <path d="M20 110 L100 110 L95 120 L25 120 Z" fill="#18181b" stroke="currentColor" strokeWidth="2" />
          <line x1="45" y1="120" x2="45" y2="135" stroke="currentColor" strokeWidth="2" />
          {/* Target mark */}
          <circle cx="60" cy="88" r="8" stroke="#ef4444" strokeWidth="1.5" />
          <line x1="60" y1="76" x2="60" y2="100" stroke="#ef4444" strokeWidth="1" />
          <line x1="48" y1="88" x2="72" y2="88" stroke="#ef4444" strokeWidth="1" />
          <text x="60" y="150" fill="#3b82f6" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">猎人 (HUNTER)</text>
        </svg>
      );
    case "狼人":
      return (
        <svg viewBox="0 0 120 160" className="w-full h-full text-zinc-100 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="5" width="110" height="150" rx="3" stroke="#ef4444" strokeWidth="3" />
          {/* Snarl Werewolf Jaws */}
          <path d="M30 60 C30 30 90 30 90 60 C90 75 80 90 75 105 L45 105 C40 90 30 75 30 60 Z" fill="#09090b" stroke="currentColor" strokeWidth="2.5" />
          {/* Sharp Fangs */}
          <path d="M42 63 L47 73 L52 63 L57 73 L62 63 L67 73 L72 63 L77 73 L82 63" stroke="#ef4444" strokeWidth="1.5" />
          {/* Slavering glowing red beast eyes */}
          <path d="M40 48 Q50 43 54 50" stroke="#f43f5e" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M80 48 Q70 43 66 50" stroke="#f43f5e" strokeWidth="2.5" strokeLinecap="round" />
          {/* Ripped gashes */}
          <path d="M15 15 L35 30" stroke="#ef4444" strokeWidth="2" />
          <path d="M22 12 L42 27" stroke="#ef4444" strokeWidth="2" />
          <text x="60" y="150" fill="#f43f5e" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">狼人 (WEREWOLF)</text>
        </svg>
      );
    default:
      // Villager / Farmer
      return (
        <svg viewBox="0 0 120 160" className="w-full h-full text-zinc-100 bg-zinc-950" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="5" width="110" height="150" rx="3" stroke="#10b981" strokeWidth="3" />
          {/* Farmer Straw Hat */}
          <path d="M20 60 C20 40 100 40 100 60 Z" fill="#27272a" stroke="currentColor" strokeWidth="2" />
          <path d="M10 60 L110 60 L100 65 L20 65 Z" fill="#18181b" stroke="currentColor" strokeWidth="2" />
          {/* Pitchfork pitch */}
          <path d="M40 120 L80 120 M50 90 L50 120 M70 90 L70 120 M60 80 L60 140" stroke="currentColor" strokeWidth="2" />
          {/* Radiant Lantern glow */}
          <circle cx="60" cy="95" r="10" fill="#14532d" stroke="#10b981" strokeWidth="1.5" />
          <path d="M60 85 L60 105 M50 95 L70 95" stroke="#10b981" strokeWidth="1" />
          <text x="60" y="150" fill="#10b981" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">村民 (VILLAGER)</text>
        </svg>
      );
  }
}

export default function CardDeck() {
  const snapshot = useGameStore((s) => s.snapshot);
  const revealView = useGameStore((s) => s.revealView);
  const players = snapshot?.players || [];

  return (
    <div className="flex flex-col h-full w-full max-w-[280px] bg-[#050505]/75 backdrop-blur-md px-3 py-4 select-none relative z-10 shrink-0 shadow-2xl overflow-y-auto woodcut-texture">
      <div className="border-b-4 border-black pb-3 mb-4 text-center">
        <h2 className="font-sans font-extrabold tracking-widest text-red-600 text-lg uppercase ink-shadow">⚔ 席位卡牌 ⚔</h2>
        <p className="font-mono text-[9px] text-[#e0e0e0]/70 tracking-widest uppercase mt-1">
          {revealView === "god" ? "God View" : "Suspense"}
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {players.map((p) => {
          // 上帝视角：始终亮身份；悬念模式：仅死亡或终局亮身份
          const isExposed = revealView === "god" || !p.is_alive || !!snapshot?.winner;
          const roleStr = p.role || "未知";
          let roleColor = "text-zinc-400";
          if (isExposed) {
            if (roleStr.includes("狼")) roleColor = "text-red-500 font-bold ink-shadow";
            else if (roleStr.includes("预言")) roleColor = "text-[#c084fc] font-bold ink-shadow";
            else if (roleStr.includes("女巫")) roleColor = "text-[#eab308] font-bold ink-shadow";
            else if (roleStr.includes("猎人")) roleColor = "text-[#3b82f6] font-bold ink-shadow";
            else roleColor = "text-[#10b981] font-bold ink-shadow";
          }

          return (
            <div key={p.seat}
              className={`group flex items-center bg-[#111] transition-all duration-300 rounded ${
                !p.is_alive ? "opacity-55 border-black/80 scale-95 border-2"
                : p.is_sheriff ? "border-yellow-500 border-2 ring-1 ring-yellow-500/50"
                : "manga-border"
              }`}>
              <div className="p-2 flex flex-col justify-center items-center h-full border-r border-black w-10 text-center bg-black text-[#e0e0e0]/50">
                <span className="font-mono text-xs font-bold">{p.seat}</span>
                {p.is_sheriff && <span className="text-[8px] text-yellow-500 font-bold mt-0.5">警</span>}
              </div>

              <div className="w-16 h-20 shrink-0 overflow-hidden relative border-r border-[#222]">
                <RoleIllustration roleColor={roleColor} role={isExposed ? roleStr : ""} isExposed={isExposed} />
                {!p.is_alive && (
                  <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
                    <span className="text-[10px] text-red-600 font-extrabold tracking-widest border-2 border-red-700/80 px-1 py-0.5 uppercase bg-black rotate-12">出局</span>
                  </div>
                )}
              </div>

              <div className="p-2 flex-grow min-w-0">
                <h3 className="font-sans font-black text-xs truncate text-[#e0e0e0]">{p.name}</h3>
                <p className="font-mono text-[9px] mt-1 text-[#e0e0e0]/70 truncate">
                  役：<span className={roleColor}>{isExposed ? roleStr : "未知秘匿"}</span>
                </p>
                {p.model && (
                  <p className="font-mono text-[8px] text-zinc-500 mt-0.5 truncate">🤖 {p.model}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
