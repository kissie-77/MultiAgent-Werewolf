import type { BeliefSnapshot } from "../api/insightTypes";
import type { InsightPlayer } from "./insightMap";

export type WolfStance = "sacrifice" | "bus" | "counter" | "hide" | "push";

export interface WolfSuspector {
  seat: number;
  prob: number;
}

export interface WolfExposureRow {
  wolfSeat: number;
  role: string;
  exposure: number;
  topSuspectors: WolfSuspector[];
  stance: WolfStance;
}

const SUSPECTOR_CO_LEADER_DELTA = 0.15;

/** 阈值镜像后端 strategy/wolf/camp_mind.py `_stance_from_exposure`。 */
export function stanceFromExposure(p: number): WolfStance {
  if (p >= 0.85) return "sacrifice";
  if (p >= 0.6) return "bus";
  if (p >= 0.45) return "counter";
  if (p >= 0.25) return "hide";
  return "push";
}

/**
 * 从当前帧信念矩阵派生每只存活狼的暴露雷达。
 * 暴露列 = 非狼存活观察者对该狼的 wolf_probability（排除狼队友与自身）。
 */
export function selectWolfExposure(
  beliefs: BeliefSnapshot[] | null,
  players: InsightPlayer[],
): WolfExposureRow[] {
  if (!beliefs || beliefs.length === 0 || !players || players.length === 0) return [];

  const wolves = players.filter((p) => p.camp === "werewolf" && p.alive);
  if (wolves.length === 0) return [];

  const playerBySeat = new Map<number, InsightPlayer>();
  for (const p of players) playerBySeat.set(p.seat, p);

  const rows: WolfExposureRow[] = wolves.map((wolf) => {
    const column: WolfSuspector[] = [];
    for (const snap of beliefs) {
      const obs = snap.observer_seat;
      if (obs === wolf.seat) continue; // 自身
      if (playerBySeat.get(obs)?.camp === "werewolf") continue; // 狼队友
      const cell = snap.first_order.find((f) => f.target_seat === wolf.seat);
      if (cell) column.push({ seat: obs, prob: cell.wolf_probability });
    }

    const exposure = column.length
      ? column.reduce((m, c) => (c.prob > m ? c.prob : m), 0)
      : 0;

    const sorted = [...column].sort((a, b) => b.prob - a.prob || a.seat - b.seat);
    const topSuspectors: WolfSuspector[] = [];
    if (sorted[0] && sorted[0].prob > 0) {
      topSuspectors.push(sorted[0]);
      const second = sorted[1];
      if (second && second.prob > 0 && second.prob >= sorted[0].prob - SUSPECTOR_CO_LEADER_DELTA) {
        topSuspectors.push(second);
      }
    }

    return {
      wolfSeat: wolf.seat,
      role: wolf.role,
      exposure,
      topSuspectors,
      stance: stanceFromExposure(exposure),
    };
  });

  return rows.sort((a, b) => b.exposure - a.exposure || a.wolfSeat - b.wolfSeat);
}
