import type { BeliefSnapshot } from "../api/insightTypes";
import type { InsightPlayer } from "../lib/insightMap";
import { selectWolfExposure, type WolfStance } from "../lib/wolfExposure";
import { heatColor, formatWolfProb } from "../lib/beliefFormat";

interface Props {
  beliefs: BeliefSnapshot[];
  players: InsightPlayer[];
}

const STANCE_LABEL: Record<WolfStance, string> = {
  sacrifice: "🩸 弃车",
  bus: "🚌 卖队友",
  counter: "⚔️ 对抗悍跳",
  hide: "🙈 隐藏",
  push: "😎 带节奏",
};

const WOLF_ROLE_ZH: Record<string, string> = {
  Werewolf: "狼人",
  AlphaWolf: "狼王",
  WhiteWolf: "白狼",
  WolfBeauty: "狼美人",
  GuardianWolf: "守卫狼",
  HiddenWolf: "隐狼",
  BloodMoonApostle: "血月使徒",
  NightmareWolf: "梦魇狼",
};

function wolfRoleZh(role: string): string {
  return WOLF_ROLE_ZH[role.replace(/\s+/g, "")] ?? "狼";
}

export default function WolfExposurePanel({ beliefs, players }: Props) {
  const rows = selectWolfExposure(beliefs, players);
  if (rows.length === 0) return null;

  return (
    <div className="mt-2 border border-rose-900/40 bg-[#0a0808]/90 rounded-md overflow-hidden text-rose-100 text-[10px]">
      <div className="flex justify-between items-center px-3 py-1.5 border-b border-rose-900/50 bg-zinc-950/80">
        <span className="font-serif font-black tracking-widest text-rose-400">🐺 狼队·暴露雷达</span>
        <span className="text-rose-500/70 text-[9px]">谁快暴露了</span>
      </div>
      <div className="p-2 flex flex-col gap-1.5">
        {rows.map((r) => (
          <div key={r.wolfSeat} className="flex items-center gap-2">
            <span className="font-serif font-bold text-rose-200 w-16 shrink-0">
              P{r.wolfSeat} {wolfRoleZh(r.role)}
            </span>
            <div className="flex-1 h-2.5 rounded-sm bg-black/50 overflow-hidden border border-rose-900/30">
              <div
                className="h-full rounded-sm transition-[width] duration-500"
                style={{ width: `${Math.round(r.exposure * 100)}%`, backgroundColor: heatColor(r.exposure) }}
              />
            </div>
            <span className="font-mono text-rose-100 w-9 text-right shrink-0">{formatWolfProb(r.exposure)}</span>
            <span className="text-rose-300/80 w-20 shrink-0 truncate">
              最疑 {r.topSuspectors.length ? r.topSuspectors.map((s) => `P${s.seat}`).join(",") : "—"}
            </span>
            <span className="shrink-0 font-sans text-rose-200">{STANCE_LABEL[r.stance]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
