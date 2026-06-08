import { BeliefSnapshot } from "../api/insightTypes";
import { selectExposureRow } from "../lib/insightMap";
import { heatColor, formatWolfProb } from "../lib/beliefFormat";

interface Props {
  beliefs: BeliefSnapshot[];
  speakerSeat: number | null;
}

export default function ExposureRadarStrip({ beliefs, speakerSeat }: Props) {
  const cells = selectExposureRow(beliefs, speakerSeat);
  const title = speakerSeat == null ? "被怀疑雷达" : `被怀疑雷达 · P${speakerSeat}视角`;

  return (
    <div className="mt-2 border border-amber-900/30 bg-[#0a0808]/90 rounded-md overflow-hidden text-amber-100 text-[10px]">
      <div className="flex justify-between items-center px-3 py-1.5 border-b border-amber-900/40 bg-zinc-950/80">
        <span className="font-serif font-black tracking-widest text-[#d4af37]">{title}</span>
        <span className="text-amber-500/70 text-[9px]">谁在怀疑“我”</span>
      </div>
      <div className="p-2 flex flex-wrap gap-1">
        {speakerSeat == null ? (
          <span className="text-amber-700/70 px-1 py-1">等待发言…</span>
        ) : cells.length === 0 ? (
          <span className="text-amber-700/70 px-1 py-1">{`P${speakerSeat} 暂未记录被谁怀疑`}</span>
        ) : (
          cells.map((c) => (
            <div
              key={c.observer_seat}
              className="group relative flex items-center gap-1 px-1.5 py-0.5 rounded-sm border border-amber-900/30 cursor-crosshair"
              style={{ backgroundColor: heatColor(c.suspicion) }}
            >
              <span className="font-serif font-bold text-white drop-shadow-[0_1px_1.5px_rgba(0,0,0,0.9)]">P{c.observer_seat}</span>
              <span className="font-mono text-white drop-shadow-[0_1px_1.5px_rgba(0,0,0,0.9)]">{formatWolfProb(c.suspicion)}</span>
              {c.reason && (
                <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity z-50 bg-[#0f0a05] border border-amber-900/60 text-amber-100 px-2 py-1.5 rounded-sm bottom-full mb-1 left-0 shadow-[0_5px_15px_rgba(0,0,0,0.8)] pointer-events-none w-max max-w-[200px] whitespace-normal break-words">
                  {c.reason}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
