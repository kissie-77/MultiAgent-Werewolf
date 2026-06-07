import { useGameStore } from "../store";
import { NIGHT_SUB_PHASE_LABEL } from "../lib/liveCue";

/**
 * Minimal DOM anchors for animators — attach effects via data-live-cue attributes.
 * Not meant as final UI; values mirror `gameState.liveCue` from the SSE reducer.
 */
export default function LiveCueAnchors() {
  const liveCue = useGameStore((s) => s.state?.liveCue);
  if (!liveCue) return null;

  const { nightSubPhase, nightSkill, sheriffStage } = liveCue;

  if (!nightSubPhase && !nightSkill && !sheriffStage) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[15] flex flex-col gap-1 items-end">
      {sheriffStage && (
        <div
          data-live-cue="sheriff-stage"
          data-stage={sheriffStage}
          className="font-mono text-[9px] text-amber-500/80 uppercase tracking-widest bg-black/60 px-2 py-0.5 rounded border border-amber-900/40"
        >
          警长阶段 · {sheriffStage === "campaign" ? "竞选发言" : "投票"}
        </div>
      )}
      {nightSubPhase && (
        <div
          data-live-cue="night-sub-phase"
          data-name={nightSubPhase}
          className="font-mono text-[9px] text-violet-400/80 uppercase tracking-widest bg-black/60 px-2 py-0.5 rounded border border-violet-900/40"
        >
          夜间环节 · {NIGHT_SUB_PHASE_LABEL[nightSubPhase] ?? nightSubPhase}
        </div>
      )}
      {nightSkill && (
        <div
          data-live-cue="night-skill"
          data-seat={nightSkill.seat}
          data-role={nightSkill.role}
          data-sub-phase={nightSkill.subPhase ?? ""}
          className="font-mono text-[9px] text-fuchsia-400/80 uppercase tracking-widest bg-black/60 px-2 py-0.5 rounded border border-fuchsia-900/40"
        >
          技能占位 · {nightSkill.seat}号 {nightSkill.role}
        </div>
      )}
    </div>
  );
}
