import type { EffectType } from "../types";
import type { CoarseStage } from "../lib/phaseStage";

export type SfxId = string;

/** 技能 effectType → sfx 文件 id。 */
export const effectTypeSfx: Record<EffectType, SfxId> = {
  bite: "skill_bite",
  inspect: "skill_inspect",
  heal: "skill_heal",
  poison: "skill_poison",
  shoot: "skill_shoot",
  vote: "skill_vote",
  rally: "skill_vote",
  guard: "skill_guard",
  charm: "skill_charm",
  mark: "skill_mark",
  link: "skill_link",
  duel: "skill_duel",
  swap: "skill_swap",
  corpse: "skill_corpse",
  fear: "skill_fear",
};

/** 公共事件 event_type → 事件 sfx 文件 id（非技能）。null = 不出声。 */
export function eventSfx(ev: { event_type: string; data?: Record<string, unknown> }): SfxId | null {
  switch (ev.event_type) {
    case "game_started": return "event_game_start";
    case "player_died": return "event_death_reveal";
    case "player_eliminated": return "event_execution";
    case "vote_result": return "event_vote_tally";
    case "sheriff_elected": return "event_sheriff_elected";
    case "sheriff_tie": return "event_vote_tie";
    case "lover_died": return "event_lover_death";
    case "game_ended":
      return ev.data?.winner_camp === "villager" ? "event_victory_good" : "event_victory_evil";
    default:
      return null;
  }
}

/** 粗阶段 → 转场 sfx（仅 nightfall/dawn）。 */
export function stageSfx(stage: CoarseStage): SfxId | null {
  if (stage === "night") return "event_nightfall";
  if (stage === "day") return "event_dawn";
  return null;
}

/** 背景音乐文件 id（按需懒加载，不进 ALL_SFX_IDS 预加载——单首约 2.8MB）。 */
export const BGM_IDS: SfxId[] = [
  "bgm_lobby", "bgm_night", "bgm_day", "bgm_tension", "bgm_settlement",
];

/**
 * 当前 phase → 背景音乐 id。
 * 对局外（信息页 / 未连接）传 null → 大厅曲。投票/警长公投用张力曲,终局用结算曲。
 */
export function bgmIdForPhase(phase: string | null | undefined): SfxId {
  switch (phase) {
    case "NIGHT_WOLF":
    case "NIGHT_SEER":
    case "NIGHT_WITCH":
      return "bgm_night";
    case "DAY_VOTE":
    case "DAY_SHERIFF_VOTE":
      return "bgm_tension";
    case "DAY_SHERIFF_RUN":
    case "DAY_ANNOUNCEMENT":
    case "DAY_DEBATE":
      return "bgm_day";
    case "GAME_OVER":
      return "bgm_settlement";
    case "START_SCREEN":
    case "ROLE_CHOICE":
    default:
      return "bgm_lobby";
  }
}

/** 磁盘上有文件的全部 id（供预加载）。 */
export const ALL_SFX_IDS: SfxId[] = [
  "skill_bite", "skill_inspect", "skill_heal", "skill_poison", "skill_shoot", "skill_vote",
  "skill_guard", "skill_charm", "skill_mark", "skill_link", "skill_duel", "skill_swap",
  "skill_corpse", "skill_fear",
  "event_game_start", "event_death_reveal", "event_execution", "event_vote_tally",
  "event_sheriff_elected", "event_nightfall", "event_dawn", "event_victory_good",
  "event_victory_evil", "event_lover_death", "event_vote_tie",
  "ui_click", "ui_hover", "ui_panel_open", "ui_panel_close", "ui_error", "ui_submit",
  "ui_your_turn", "ui_tick", "ui_timeout",
];

export function sfxPath(id: SfxId): string {
  return `/audio/${id}.mp3`;
}

/** 滑窗 burst 门：窗口内允许至多 max 次，超出抑制。 */
export function createBurstGate(windowMs = 700, max = 3) {
  let times: number[] = [];
  return {
    allow(nowMs: number): boolean {
      times = times.filter((t) => nowMs - t < windowMs);
      const ok = times.length < max;
      times.push(nowMs);
      return ok;
    },
  };
}

/** event_id 单调去重（挡 EventSource 重连补发）。 */
export function createEventDedup() {
  let last = -1;
  return {
    seen(eventId?: number): boolean {
      if (eventId == null) return false;
      if (eventId <= last) return true;
      last = eventId;
      return false;
    },
  };
}
