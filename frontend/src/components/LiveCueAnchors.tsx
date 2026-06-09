import React from "react";
import { Moon, Swords, Crown } from "lucide-react";
import { useGameStore } from "../store";
import { NIGHT_SUB_PHASE_LABEL } from "../lib/liveCue";
import { isRoleRevealed } from "../lib/humanPrompt";

/**
 * Minimal DOM anchors for animators — attach effects via data-live-cue attributes.
 * In seat view, role names are hidden unless revealed to the human player.
 */
export default React.memo(function LiveCueAnchors() {
  const liveCue = useGameStore((s) => s.state?.liveCue);
  const humanSeat = useGameStore((s) => s.humanSeat);
  const isSeatView = humanSeat != null;

  if (!liveCue) return null;

  const { nightSubPhase, nightSkill, sheriffStage } = liveCue;

  if (!nightSubPhase && !nightSkill && !sheriffStage) return null;

  const showRole = (seat: number, role: string) =>
    !isSeatView || seat === humanSeat || isRoleRevealed(role);

  return (
    <div className="pointer-events-none fixed bottom-[72px] right-4 z-[15] flex flex-col gap-1.5 items-end">
      {sheriffStage && (
        <div
          data-live-cue="sheriff-stage"
          data-stage={sheriffStage}
          className="flex items-center gap-1.5 bg-[#0a0807]/90 bg-woodcut-dark border border-amber-600/50 rounded-sm px-2.5 py-1 shadow-[inset_0_1px_2px_rgba(255,255,255,0.06),2px_2px_0_rgba(0,0,0,0.55)]"
        >
          <Crown className="w-3.5 h-3.5 shrink-0 text-amber-400 drop-shadow-[0_0_5px_rgba(245,158,11,0.6)]" />
          <span className="font-display-cn text-[11px] tracking-widest text-amber-200">
            警长阶段 · {sheriffStage === "campaign" ? "竞选发言" : "投票"}
          </span>
        </div>
      )}
      {nightSubPhase && (
        <div
          data-live-cue="night-sub-phase"
          data-name={nightSubPhase}
          className="flex items-center gap-1.5 bg-[#0a0807]/90 bg-woodcut-dark border border-violet-700/50 rounded-sm px-2.5 py-1 shadow-[inset_0_1px_2px_rgba(255,255,255,0.06),2px_2px_0_rgba(0,0,0,0.55)]"
        >
          <Moon className="w-3.5 h-3.5 shrink-0 text-violet-300 drop-shadow-[0_0_5px_rgba(139,92,246,0.6)] animate-pulse" />
          <span className="font-display-cn text-[11px] tracking-widest text-violet-200">
            夜间环节 · {NIGHT_SUB_PHASE_LABEL[nightSubPhase] ?? nightSubPhase}
          </span>
        </div>
      )}
      {nightSkill && (
        <div
          data-live-cue="night-skill"
          data-seat={nightSkill.seat}
          data-role={showRole(nightSkill.seat, nightSkill.role) ? nightSkill.role : ""}
          data-sub-phase={nightSkill.subPhase ?? ""}
          className="flex items-center gap-1.5 bg-[#0a0807]/90 bg-woodcut-dark border border-rose-800/55 rounded-sm px-2.5 py-1 shadow-[inset_0_1px_2px_rgba(255,255,255,0.06),2px_2px_0_rgba(0,0,0,0.55)]"
        >
          <Swords className="w-3.5 h-3.5 shrink-0 text-rose-400 drop-shadow-[0_0_5px_rgba(244,63,94,0.6)]" />
          <span className="font-display-cn text-[11px] tracking-widest text-rose-200">
            夜间行动 · {nightSkill.seat}号
            {showRole(nightSkill.seat, nightSkill.role) && nightSkill.role ? ` ${nightSkill.role}` : ""}
          </span>
        </div>
      )}
    </div>
  );
})