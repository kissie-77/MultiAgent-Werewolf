import type { InsightPlayer } from "../lib/insightMap";
import {
  GOD_ROLES,
  GOD_ROLE_ZH,
  PRIORITY_LABEL,
  selectGodRoleRows,
  type GodRolePriority,
  type WolfCampMindV2,
} from "../lib/godRoleIntel";
import { heatColor, formatWolfProb } from "../lib/beliefFormat";

interface Props {
  /** 一只狼的私有面板（wolf_camp_mind_v2 行）。 */
  record: WolfCampMindV2;
  /** 可选：真实 roster，用于在目标行旁标注真实身份（god 视角对照）。 */
  players?: InsightPlayer[];
}

const PRIORITY_CLASS: Record<GodRolePriority, string> = {
  kill_tonight: "text-rose-300 border-rose-700/60 bg-rose-950/40",
  watch: "text-amber-300 border-amber-700/50 bg-amber-950/30",
  low: "text-zinc-400 border-zinc-700/50 bg-zinc-900/40",
};

/** 真实角色英文 → 中文（仅用于 demo 对照标注）。 */
const ROLE_ZH: Record<string, string> = {
  Seer: "预言家",
  Witch: "女巫",
  Guard: "守卫",
  Hunter: "猎人",
  Villager: "平民",
  Werewolf: "狼人",
  AlphaWolf: "狼王",
  WhiteWolf: "白狼",
  WolfBeauty: "狼美人",
};

function realRoleZh(role: string | undefined): string {
  if (!role) return "";
  return ROLE_ZH[role.replace(/\s+/g, "")] ?? role;
}

export default function GodRoleIntelPanel({ record, players }: Props) {
  const rows = selectGodRoleRows(record);
  const roleBySeat = new Map<number, string>();
  if (players) for (const p of players) roleBySeat.set(p.seat, p.role);

  return (
    <div className="border border-rose-900/40 bg-[#0a0808]/90 rounded-md overflow-hidden text-rose-100 text-[11px]">
      <div className="flex justify-between items-center px-3 py-1.5 border-b border-rose-900/50 bg-zinc-950/80">
        <span className="font-serif font-black tracking-widest text-rose-400">
          🔪 P{record.owner_seat}号狼 · 神职猜测
        </span>
        <span className="text-rose-500/70 text-[9px]">R{record.round} · 谁是神职</span>
      </div>

      {rows.length === 0 ? (
        <div className="px-3 py-4 text-center text-zinc-500 text-[10px]">（本狼暂无神职推断）</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[10px]">
            <thead>
              <tr className="text-rose-300/70">
                <th className="text-left font-sans font-normal px-2 py-1 sticky left-0 bg-[#0a0808]/95">目标</th>
                {GOD_ROLES.map((role) => (
                  <th key={role} className="font-sans font-normal px-1 py-1 text-center w-12">
                    {GOD_ROLE_ZH[role]}
                  </th>
                ))}
                <th className="font-sans font-normal px-2 py-1 text-center w-20">威胁</th>
                <th className="font-sans font-normal px-2 py-1 text-center w-16">处置</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const real = realRoleZh(roleBySeat.get(r.targetSeat));
                return (
                  <tr key={r.targetSeat} className="border-t border-rose-900/20">
                    <td className="px-2 py-1 sticky left-0 bg-[#0a0808]/95 whitespace-nowrap">
                      <span className="font-serif font-bold text-rose-200">P{r.targetSeat}</span>
                      {real && <span className="ml-1 text-zinc-500 text-[9px]">({real})</span>}
                    </td>
                    {GOD_ROLES.map((role) => {
                      const p = r.distribution[role];
                      const isTop = role === r.topRole && r.topProb > 0;
                      return (
                        <td key={role} className="px-1 py-1 text-center">
                          <span
                            className={`inline-block w-10 py-0.5 rounded-sm font-mono ${
                              isTop ? "ring-1 ring-rose-300/80 font-bold" : ""
                            }`}
                            style={{
                              backgroundColor: heatColor(p),
                              color: p > 0.45 ? "#0a0808" : "#fbcfe8",
                            }}
                          >
                            {formatWolfProb(p)}
                          </span>
                        </td>
                      );
                    })}
                    <td className="px-2 py-1">
                      <div className="flex items-center gap-1.5">
                        <div className="flex-1 h-2 rounded-sm bg-black/50 overflow-hidden border border-rose-900/30">
                          <div
                            className="h-full rounded-sm transition-[width] duration-500"
                            style={{
                              width: `${Math.round(r.threat * 100)}%`,
                              backgroundColor: heatColor(r.threat),
                            }}
                          />
                        </div>
                        <span className="font-mono text-rose-100 w-8 text-right">{formatWolfProb(r.threat)}</span>
                      </div>
                    </td>
                    <td className="px-2 py-1 text-center">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded border text-[9px] font-sans whitespace-nowrap ${PRIORITY_CLASS[r.priority]}`}
                      >
                        {PRIORITY_LABEL[r.priority]}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* 最高威胁目标的推断依据（evidence） */}
          {rows[0]?.evidence.length > 0 && (
            <div className="px-3 py-1.5 border-t border-rose-900/30 text-rose-300/70 text-[9px] leading-relaxed">
              <span className="text-rose-500/80">依据 P{rows[0].targetSeat}：</span>
              {rows[0].evidence.join("；")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
