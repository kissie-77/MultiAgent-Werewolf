import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useGameStore } from "../store";
import { getTarotImage } from "../utils/roles";
import { isRoleRevealed } from "../lib/humanPrompt";
import { playToggle } from "../lib/uiSound";

/** Corner HUD for the seated human: role tarot + remaining potions + collapsible raw detail.
 *  Click the card itself to collapse it down to a small tarot thumbnail (so it never blocks
 *  the central speech area); click the thumbnail to expand again. Toggling plays the cue. */
export default function IdentityHud() {
  const players = useGameStore((s) => s.state?.players ?? []);
  const pendingInput = useGameStore((s) => s.pendingInput);
  const [open, setOpen] = useState(false);
  // Whole-card collapse: false = expanded (default, so the player sees their role at once).
  const [collapsed, setCollapsed] = useState(false);

  const me = players.find((p) => p.isUser);
  const role = pendingInput?.self_role || me?.role || "";
  if (!isRoleRevealed(role)) return null;

  const potions = pendingInput?.remaining_potions;
  const rawDetail = pendingInput?.prompt?.trim();

  const toggleCollapsed = () => { playToggle(collapsed); setCollapsed((c) => !c); };

  // ── Collapsed: just a small tarot thumbnail; click to expand. ──
  if (collapsed) {
    return (
      <div className="absolute top-20 right-4 z-[105] pointer-events-auto">
        <button
          type="button"
          onClick={toggleCollapsed}
          title="展开身份卡"
          aria-label="展开身份卡"
          className="block rounded-md border border-amber-700/50 bg-slate-950/80 bg-woodcut-dark shadow-lg backdrop-blur-md p-1 hover:border-amber-500/70 transition-colors cursor-pointer"
        >
          <img src={getTarotImage(role)} alt={role} className="w-10 h-14 object-cover rounded-sm" />
        </button>
      </div>
    );
  }

  // ── Expanded: full card. Click the identity row to collapse it. ──
  return (
    <div className="absolute top-20 right-4 z-[105] w-56 pointer-events-auto">
      <div className="bg-slate-950/90 bg-woodcut-dark border border-amber-700/50 rounded-lg shadow-xl p-3 backdrop-blur-md">
        <div
          role="button"
          tabIndex={0}
          onClick={toggleCollapsed}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggleCollapsed();
            }
          }}
          title="点击收起身份卡"
          className="flex items-center gap-3 cursor-pointer select-none"
        >
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
              onClick={(e) => { e.stopPropagation(); playToggle(!open); setOpen((v) => !v); }}
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
