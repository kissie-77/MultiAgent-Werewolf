import type { GameState } from "../types";

export type CoarseStage = "lobby" | "night" | "day" | "over";

/** Interval (ms) below which back-to-back stage changes are treated as an
 * initial replay burst (connecting to an in-progress run) and skip the card. */
export const MIN_GAP_MS = 1200;
export const CARD_MS = 1800;
export const ESTABLISH_MS = 1100;
export const DAY_DEATH_DELAY_MS = 500;

export function coarseStage(phase: GameState["phase"]): CoarseStage {
  if (phase === "START_SCREEN" || phase === "ROLE_CHOICE") return "lobby";
  if (phase === "NIGHT_WOLF" || phase === "NIGHT_SEER" || phase === "NIGHT_WITCH") return "night";
  if (phase === "GAME_OVER") return "over";
  return "day";
}

/** True when entering night/day is a genuine, non-burst boundary worth a card. */
export function shouldShowCard(
  prev: CoarseStage,
  next: CoarseStage,
  gapMs: number,
  minGapMs: number,
): boolean {
  if (next !== "night" && next !== "day") return false;
  if (prev === next) return false;
  if (gapMs < minGapMs) return false;
  return true;
}

export interface StageCard {
  kicker: string;
  title: string;
  sub: string;
  death: boolean;
  victimSeat: number | null;
}

export function stageCardText(
  stage: CoarseStage,
  dayNumber: number,
  victimSeat: number | null,
): StageCard | null {
  if (stage === "night") {
    return { kicker: "夜幕降临", title: `第 ${dayNumber} 夜`, sub: "屏息", death: false, victimSeat: null };
  }
  if (stage === "day") {
    if (victimSeat != null) {
      return { kicker: "曙光破晓", title: `第 ${dayNumber} 日`, sub: `${victimSeat} 号遇害`, death: true, victimSeat };
    }
    return { kicker: "曙光破晓", title: `第 ${dayNumber} 日`, sub: "黎明", death: false, victimSeat: null };
  }
  return null;
}

const PHASE_LABEL: Record<GameState["phase"], string> = {
  START_SCREEN: "等待入场",
  ROLE_CHOICE: "宿命契约抉择",
  NIGHT_WOLF: "狼人潜行屠杀",
  NIGHT_SEER: "神灵探秘查验",
  NIGHT_WITCH: "女巫配药抉择",
  DAY_SHERIFF_RUN: "警徽竞选演说",
  DAY_SHERIFF_VOTE: "警长封印公投",
  DAY_ANNOUNCEMENT: "审判布告死讯",
  DAY_DEBATE: "圆形议事辩驳",
  DAY_VOTE: "封印放逐公投",
  GAME_OVER: "审判宿命终结",
};

export interface StageBadge {
  icon: "moon" | "sun" | "wait";
  dayText: string;
  phaseText: string;
}

export function stageBadge(phase: GameState["phase"], dayNumber: number): StageBadge {
  const stage = coarseStage(phase);
  if (stage === "night") {
    return { icon: "moon", dayText: `第 ${dayNumber} 夜`, phaseText: PHASE_LABEL[phase] };
  }
  if (stage === "day") {
    return { icon: "sun", dayText: `第 ${dayNumber} 日`, phaseText: PHASE_LABEL[phase] };
  }
  if (stage === "over") {
    return { icon: "sun", dayText: "终局", phaseText: PHASE_LABEL[phase] };
  }
  return { icon: "wait", dayText: "候场集结", phaseText: "等待入场" };
}
