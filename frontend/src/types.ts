// ===== Engine-driven game API contract (mirrors docs/.../engine-driven-game-api-design §5) =====

export enum GamePhase {
  setup = "setup",
  night = "night",
  sheriff_election = "sheriff_election",
  day_discussion = "day_discussion",
  day_voting = "day_voting",
  ended = "ended",
}

export enum PlayState {
  playing = "playing",
  paused = "paused",
}

export type SessionStatus = "running" | "paused" | "ended" | "cancelled" | "error";
export type SubPhase =
  | "werewolf_chat" | "witch_decide" | "seer_check" | "guard_decide"
  | "hunter_decide" | "graveyard_check" | string;

export type RevealMode = "now" | "on_death" | "on_game_end";
export type Visibility = "public" | "wolf" | "god";

export type StreamEventType =
  | "speech" | "skill" | "vote" | "death" | "phase" | "sub_phase"
  | "belief" | "vote_intention" | "system";

export type SkillKind =
  | "wolf_kill" | "white_wolf_kill" | "wolf_beauty_charm" | "nightmare_block"
  | "guardian_wolf_guard" | "raven_mark" | "witch_save" | "witch_poison"
  | "seer_check" | "guard" | "graveyard_check" | "hunter_shoot" | "badge_transfer"
  | string;

export const PHASE_LABELS: Record<GamePhase, string> = {
  [GamePhase.setup]: "准备",
  [GamePhase.night]: "黑夜",
  [GamePhase.sheriff_election]: "警长竞选",
  [GamePhase.day_discussion]: "白天讨论",
  [GamePhase.day_voting]: "白天投票",
  [GamePhase.ended]: "对局结束",
};

export const SUB_PHASE_LABELS: Record<string, string> = {
  werewolf_chat: "狼人夜聊中",
  witch_decide: "女巫决策中",
  seer_check: "预言家查验中",
  guard_decide: "守卫守护中",
  hunter_decide: "猎人决策中",
  graveyard_check: "盗墓查验中",
};

export interface StatePlayer {
  seat: number;
  name: string;
  role: string | null;
  camp: string | null;
  is_alive: boolean;
  is_sheriff: boolean;
  model: string | null;
  status_flags: string[];
}

export interface LastNight {
  // cause is `str | None` on the backend (state.py NightDeath.cause), so it can be null.
  deaths: { seat: number; cause: string | null }[];
  saved_seat: number | null;
  guarded_seat: number | null;
  poisoned_seat: number | null;
}

export interface VotesState {
  by_seat: Record<string, number>;
  tally: Record<string, number>;
}

export interface GameStateResponse {
  status: SessionStatus;
  error: string | null;
  play_state: PlayState | "playing" | "paused";
  speed: 1 | 2 | 4;
  phase: GamePhase;
  sub_phase: SubPhase | null;
  round: number;
  current_actor_seat: number | null;
  winner: string | null;
  sheriff_seat: number | null;
  alive_count: number;
  dead_count: number;
  last_night: LastNight | null;
  votes: VotesState | null;
  cursor: number;
  players: StatePlayer[];
}

// Mirrors the backend ViewEvent wire shape (models/view.py, spec §5.2). The
// stream carries `round` (NOT `day`); a `sub_phase`-type event delivers its
// display-hint text at the TOP LEVEL as `name` (NOT nested under `sub_phase`).
export interface StreamEvent {
  seq: number;
  type: StreamEventType;
  phase: GamePhase;
  round: number;
  reveal: RevealMode;
  visibility: Visibility;
  // speech
  speaker?: { seat: number | null; name?: string | null } | null;
  public_text?: string | null;
  private_thought?: string | null;
  // skill
  skill?: { kind: SkillKind; actor?: { seat: number | null }; target?: { seat: number | null }; result?: unknown } | null;
  // vote
  vote?: { voter?: { seat: number | null }; target?: { seat: number | null } } | null;
  // death
  death?: { seat: number | null; name?: string | null; cause?: string | null } | null;
  // sub_phase display-hint name (top-level per spec §5.2) / system text
  name?: string | null;
  text?: string | null;
}

export interface ControlRequest {
  action: "pause" | "resume" | "step" | "speed";
  value?: 1 | 2 | 4;
}

export interface ControlResponse {
  run_id: string;
  play_state: PlayState | "playing" | "paused";
  speed: 1 | 2 | 4;
  phase: GamePhase;
}

// ===== Per-seat LLM 配置（开局用，沿用 wolfcha ModelRef）=====

export interface SeatConfig {
  seat: number;
  name: string;
  provider: string;     // 仅前端分组；后端以 base_url 为准
  model: string;
  base_url: string;
  temperature?: number;
}

export interface ProviderPreset {
  id: string;
  label: string;
  base_url: string;
  models: string[];
}

// ===== 前端本地展示用的渲染日志条目 =====

export interface RenderLog {
  seq: number;
  kind: StreamEventType;
  round: number;
  speakerSeat: number | null;
  speakerName: string;
  text: string;            // 已揭示/遮挡处理后的展示文本
  privateThought?: string | null;
  visibility: Visibility;
}
