import type {
  BackendRunDetail,
  BackendReplayEventItem,
  BackendMvpRankItem,
  BackendReplayPageData,
} from "../api/types";
import type {
  ReplayRunInfo,
  TimelineEvent,
  MvpPlayer,
  TurningPoint,
  ReplayPageData,
} from "../api/types";

/**
 * Pure mapping layer: backend `/api/v1/pages/replay` (ReplayPageData) ->
 * the front-end `ReplayPageData` shape consumed by ReplayPage and its panels.
 *
 * Mirrors `lib/insightMap.ts`: pure functions, defensive defaults, snake->camel,
 * seat strings normalised. Slice B covers run header, timeline, MVP ranking and
 * turning points; the score / belief / vote-swing panels are filled in later
 * slices and default to empty collections here.
 */

// --- winner camp normalisation (backend lowercase -> front-end enum) ---
function toWinnerCamp(camp: string | null | undefined): "WOLVES" | "VILLAGERS" {
  const c = (camp ?? "").toString().toLowerCase();
  if (c === "werewolf" || c === "wolves" || c.includes("wolf")) return "WOLVES";
  return "VILLAGERS";
}

export function mapRunInfo(run: BackendRunDetail | null | undefined): ReplayRunInfo {
  return {
    id: run?.run_id ?? "",
    date: run?.created_at ?? "",
    duration: "",
    mode: run?.source ?? "",
    speed: "",
    initial_players: run?.player_count ?? 0,
    user_role: "",
    winner_camp: toWinnerCamp(run?.winner_camp),
  };
}

// --- timeline ---

/** God view injects these snapshot events into the timeline; hide them here. */
const REPLAY_ONLY_EVENT_TYPES = new Set(["belief_snapshot", "vote_intention_snapshot"]);

/** backend event_type -> front-end TimelineEvent.type (default "system"). */
const EVENT_KIND: Record<string, NonNullable<TimelineEvent["type"]>> = {
  player_speech: "speech",
  player_discussion: "speech",
  seer_checked: "check",
  witch_saved: "save",
  werewolf_killed: "kill",
  player_died: "kill",
  player_eliminated: "kill",
  witch_poison_used: "kill",
  vote_cast: "vote",
  vote_result: "vote",
};

/** Human-readable titles for non-speech events (fallback: the raw event_type). */
const EVENT_LABELS: Record<string, string> = {
  game_started: "游戏开始",
  game_ended: "游戏结束",
  phase_changed: "阶段切换",
  message: "旁白",
  role_acting: "角色行动",
  player_speech: "玩家发言",
  player_discussion: "玩家讨论",
  werewolf_killed: "狼人袭击",
  witch_saved: "女巫施救",
  witch_poison_used: "女巫用毒",
  seer_checked: "预言家查验",
  vote_cast: "投票",
  vote_result: "投票结果",
  player_died: "玩家死亡",
  player_eliminated: "放逐出局",
};

/**
 * Night detection is case-insensitive on purpose: the backend emits lowercase
 * phases ("night", "day_discussion"), while the front-end GameState enum uses
 * uppercase ("NIGHT_WOLF"). Both must resolve to isNight correctly.
 */
function isNightPhase(phase: string | null | undefined): boolean {
  return (phase ?? "").toString().toLowerCase().startsWith("night");
}

function eventKind(eventType: string): NonNullable<TimelineEvent["type"]> {
  return EVENT_KIND[eventType] ?? "system";
}

function mapEvent(ev: BackendReplayEventItem): TimelineEvent {
  const data = (ev.data ?? {}) as Record<string, any>;
  const type = eventKind(ev.event_type);
  const speech = typeof data.speech === "string" ? data.speech : undefined;
  const playerId = data.player_id != null ? String(data.player_id) : undefined;
  const targetId = data.target_id != null ? String(data.target_id) : undefined;
  const result = data.result != null ? String(data.result) : undefined;
  return {
    id: String(ev.index),
    day: ev.round_number ?? 0,
    isNight: isNightPhase(ev.phase),
    phase: ev.phase ?? "",
    title: EVENT_LABELS[ev.event_type] ?? ev.event_type ?? "",
    description: ev.message ?? "",
    type,
    message: speech ?? ev.message ?? "",
    ...(playerId ? { playerId } : {}),
    ...(targetId ? { targetId } : {}),
    ...(result ? { result } : {}),
  };
}

export function mapTimeline(
  events: BackendReplayEventItem[] | null | undefined,
): TimelineEvent[] {
  if (!Array.isArray(events)) return [];
  return events
    .filter((ev) => !REPLAY_ONLY_EVENT_TYPES.has(ev?.event_type))
    .map(mapEvent);
}

// --- MVP ranking ---

/** "player_5" / "5" -> 5; non-numeric -> 0. */
function toSeatNumber(playerId: string | number | null | undefined): number {
  const digits = String(playerId ?? "").replace(/\D/g, "");
  const n = parseInt(digits, 10);
  return Number.isNaN(n) ? 0 : n;
}

/**
 * NOTE: backend `total_score` is always 0.0 (known bug — real value is
 * scores[kind=="mvp"].payload.data.players[].mvp_total). This slice only maps
 * the MvpRankItem fields; the real score is wired in a later slice.
 */
export function mapMvpRanking(
  items: BackendMvpRankItem[] | null | undefined,
): MvpPlayer[] {
  if (!Array.isArray(items)) return [];
  return items.map((it) => ({
    rank: it.rank ?? 0,
    playerId: toSeatNumber(it.player_id),
    playerName: it.player_name ?? "",
    role: it.role_name ?? "",
    score: typeof it.total_score === "number" ? it.total_score : 0,
    contributionDesc: "",
    isMvp: it.rank === 1,
  }));
}

// --- turning points ---

export function mapTurningPoints(
  lines: string[] | null | undefined,
): TurningPoint[] {
  if (!Array.isArray(lines)) return [];
  return lines.map((line) => {
    const text = String(line ?? "");
    return { day: 0, title: text, desc: text };
  });
}

// --- compose ---

export function mapReplayPage(
  data: Partial<BackendReplayPageData> | null | undefined,
): ReplayPageData {
  const d = data ?? {};
  return {
    run: mapRunInfo(d.run),
    timeline: mapTimeline(d.timeline),
    phase_summary: [],
    turning_points: mapTurningPoints(d.turning_points),
    mvp_ranking: mapMvpRanking(d.mvp_ranking),
    scores: [],
    views_available: Array.isArray(d.views_available) ? d.views_available : [],
    report_markdown: d.report_markdown ?? "",
    coach_excerpt: d.coach_excerpt ?? "",
    belief_snapshots: [],
    wolf_camp_snapshots: [],
    belief_heatmap: [],
    belief_matrix_anchors: [],
    vote_swing_summary: [],
  };
}
