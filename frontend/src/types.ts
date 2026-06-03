// ===== /api/v1/games/{run_id}/view 的前端镜像类型 =====

export type ViewEventType =
  | "speech" | "skill" | "vote" | "death" | "phase" | "system" | "belief" | "vote_intention";
export type RevealMode = "now" | "on_death" | "on_game_end";
export type Visibility = "public" | "wolf" | "god";

export interface ViewPlayer {
  seat: number;
  name: string;
  role: string | null;
  camp: string | null;
  is_alive: boolean;
  is_sheriff: boolean;
  model: string | null;
  provider?: string | null;
  death?: { day?: number; phase?: string; cause?: string; reveal?: RevealMode } | null;
}

export interface ViewSnapshot {
  day: number;
  phase: string;
  phase_label: string;
  winner: string | null;
  alive_count: number;
  dead_count: number;
  sheriff_seat: number | null;
  players: ViewPlayer[];
  vote_tally?: { round?: number; counts?: Record<string, number>; result?: any } | null;
}

export interface ViewEvent {
  seq: number;
  type: ViewEventType;
  day: number;
  phase: string;
  text: string;
  speaker?: { seat: number | null; name?: string | null } | null;
  public_text?: string | null;
  private_thought?: string | null;
  skill?: { kind: string; actor?: { seat: number | null }; target?: { seat: number | null }; result?: any } | null;
  vote?: { voter?: { seat: number | null }; target?: { seat: number | null } } | null;
  death?: { seat: number | null; name?: string | null; cause?: string | null } | null;
  reveal: RevealMode;
  visibility: Visibility;
}

export interface ViewResponse {
  cursor: number;
  status: "running" | "ended" | "cancelled" | "error";
  error: string | null;
  snapshot: ViewSnapshot;
  events: ViewEvent[];
}

// ===== 逐座位 LLM 配置（开局用，参照 wolfcha ModelRef）=====

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
  kind: ViewEventType;
  day: number;
  speakerSeat: number | null;
  speakerName: string;
  text: string;            // 已揭示/遮挡处理后的展示文本
  privateThought?: string | null;
  visibility: Visibility;
}
