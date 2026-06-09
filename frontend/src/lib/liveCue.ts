import type { LiveCue, ThinkingContext } from "../types";

/** Default empty cue — animators should read `gameState.liveCue` only. */
export function initialLiveCue(): LiveCue {
  return {
    thinking: null,
    nightSubPhase: null,
    nightSkill: null,
    sheriffStage: null,
  };
}

const THINKING_CONTEXTS = new Set<ThinkingContext>([
  "day_speech",
  "sheriff_speech",
  "sheriff_vote",
  "werewolf_chat",
  "night_skill",
  "general",
]);

export function parseThinkingContext(raw: unknown): ThinkingContext {
  if (typeof raw === "string" && THINKING_CONTEXTS.has(raw as ThinkingContext)) {
    return raw as ThinkingContext;
  }
  return "general";
}

/** Human-readable labels for bottom-left status (animators may ignore). */
export const THINKING_CONTEXT_LABEL: Record<ThinkingContext, string> = {
  day_speech: "白天发言筹备",
  sheriff_speech: "警长竞选发言筹备",
  sheriff_vote: "警长投票抉择",
  werewolf_chat: "狼队夜聊酝酿",
  night_skill: "夜间技能决策",
  general: "策略推演",
};

export const NIGHT_SUB_PHASE_LABEL: Record<string, string> = {
  pre_wolf: "狼群集结潜伏",
  werewolf_kill: "狼人嗜血猎杀",
  werewolf_chat: "狼群暗语密谋",
  witch_decide: "女巫秘药熬制",
  seer_check: "先知灵视窥探",
};
