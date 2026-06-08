import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useGameStore } from "../store";
import { getTarotImage } from "../utils/roles";
import { isRoleRevealed } from "../lib/humanPrompt";

/** Corner HUD for the seated human: role tarot + remaining potions + collapsible raw detail. */
export default function IdentityHud() {
  const players = useGameStore((s) => s.state?.players ?? []);
  const pendingInput = useGameStore((s) => s.pendingInput);
  const [open, setOpen] = useState(false);

  const me = players.find((p) => p.isUser);
  const role = pendingInput?.self_role || me?.role || "";
  if (!isRoleRevealed(role)) return null;

  const potions = pendingInput?.remaining_potions;
  const rawDetail = pendingInput?.prompt?.trim();

  return (
    <div className="absolute top-20 right-4 z-[105] w-56 pointer-events-auto">
      <div className="bg-slate-950/90 bg-woodcut-dark border border-amber-700/50 rounded-lg shadow-xl p-3 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <img
            src={getTarotImage(role)}
            alt={role}
            className="w-12 h-16 object-cover rounded border border-amber-800/60 shrink-0"
          />
          <div className="flex flex-col min-w-0">
            <span className="font-mono text-[9px] text-amber-600/80 uppercase tracking-widest">本人身份</span>
            <span className="font-serif text-sm font-black text-amber-200 truncate">{role}</span>
            {potions && (
              <div className="flex gap-2 mt-1 font-mono text-[10px]">
                <span className={potions.save ? "text-emerald-300" : "text-zinc-600 line-through"}>解药</span>
                <span className={potions.poison ? "text-purple-300" : "text-zinc-600 line-through"}>毒药</span>
              </div>
            )}
          </div>
        </div>

        {rawDetail && (
          <div className="mt-2 border-t border-amber-900/30 pt-2">
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider text-amber-500/80 hover:text-amber-300 cursor-pointer"
            >
              {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              查看完整局势详情
            </button>
            {open && (
              <p className="mt-2 max-h-48 overflow-y-auto text-[11px] text-amber-100/80 leading-relaxed font-serif whitespace-pre-line">
                {rawDetail}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
