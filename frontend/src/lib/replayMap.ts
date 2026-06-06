import type {
  BackendRunDetail,
  BackendReplayEventItem,
  BackendMvpRankItem,
  BackendReplayPageData,
  BackendScoreBlock,
} from "../api/types";
import type {
  ReplayRunInfo,
  TimelineEvent,
  MvpPlayer,
  TurningPoint,
  ReplayPageData,
  PlayerScore,
  VoteSwingSpeech,
  VoteSwingEdge,
  BeliefAnchor,
  BeliefObserverSnapshot,
  BeliefTargetSnapshot,
  BeliefSnapshot,
  WolfCampSnapshot,
} from "../api/types";
// NOTE: the backend belief rows use the `insightTypes.ts` BeliefSnapshot shape
// (round/anchor/observer_seat/first_order[]), which collides by name with the
// front-end `types.ts` BeliefSnapshot (day/playerBeliefs[]). Alias to keep both
// straight inside this module.
import type { BeliefSnapshot as BackendBeliefRow } from "../api/insightTypes";

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
 * Backend `total_score` is always 0.0 (known bug — the real value lives in
 * scores[kind=="mvp"].payload.data.players[].mvp_total). When the matching mvp
 * score players are supplied (via mapReplayPage), join `mvp_total` by player_id;
 * otherwise fall back to the (likely 0.0) `total_score` for backward compat.
 */
export function mapMvpRanking(
  items: BackendMvpRankItem[] | null | undefined,
  mvpPlayers?: MvpScorePlayer[] | null,
): MvpPlayer[] {
  if (!Array.isArray(items)) return [];
  const totalById = new Map<string, number>();
  if (Array.isArray(mvpPlayers)) {
    for (const p of mvpPlayers) {
      if (p?.player_id != null) totalById.set(String(p.player_id), num(p.mvp_total));
    }
  }
  return items.map((it) => {
    const pid = String(it.player_id ?? "");
    const score = totalById.has(pid)
      ? (totalById.get(pid) as number)
      : typeof it.total_score === "number"
        ? it.total_score
        : 0;
    return {
      rank: it.rank ?? 0,
      playerId: toSeatNumber(it.player_id),
      playerName: it.player_name ?? "",
      role: it.role_name ?? "",
      score,
      contributionDesc: "",
      isMvp: it.rank === 1,
    };
  });
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

// --- shared helpers (scores / belief) ---

/** Coerce anything to a finite number; non-numeric / NaN -> 0. */
function num(x: unknown): number {
  const n = typeof x === "number" ? x : Number(x);
  return Number.isFinite(n) ? n : 0;
}

/** seat number / "player_3" -> "P3" (matches the seat->"P{n}" UI convention). */
function seatLabel(seat: string | number | null | undefined): string {
  return `P${toSeatNumber(seat)}`;
}

/** A single player row inside scores[kind=="mvp"].payload.data.players[]. */
interface MvpScorePlayer {
  player_id?: string | null;
  player_name?: string | null;
  role_name?: string | null;
  camp?: string | null;
  mvp_total?: number | null;
  breakdown_norm?: Record<string, number> | null;
}

/** Pull the `.payload.data` of the first score block with the given kind. */
function scoreBlockData(
  scores: BackendScoreBlock[] | null | undefined,
  kind: string,
): any | null {
  if (!Array.isArray(scores)) return null;
  const block = scores.find((b) => b?.kind === kind);
  return block?.payload?.data ?? null;
}

/** scores[kind=="mvp"].payload.data.players[] (defensive []). */
function mvpScorePlayers(
  data: Partial<BackendReplayPageData> | null | undefined,
): MvpScorePlayer[] {
  const mvp = scoreBlockData(data?.scores, "mvp");
  const players = mvp?.players;
  return Array.isArray(players) ? players : [];
}

// --- player scores ---

/**
 * breakdown_norm dimension key -> front-end PlayerScore field. Kept behind a
 * named constant so the 4 score-dimension labels (逻辑/伪装/协作/生存) can be
 * re-mapped in one place if the backend semantics change.
 */
const SCORE_DIMENSION = {
  logicSpeechScore: "persuasion",
  deceptionMisleaderScore: "wolf_night",
  cooperationRate: "strategy",
  gameSurvivalScore: "outcome",
} as const;

export function mapPlayerScores(
  data: Partial<BackendReplayPageData> | null | undefined,
): PlayerScore[] {
  const players = mvpScorePlayers(data);
  if (players.length === 0) return [];

  // alive status joined from run.roster by player_id (default true).
  const aliveById = new Map<string, boolean>();
  const roster = data?.run?.roster;
  if (Array.isArray(roster)) {
    for (const r of roster) {
      if (r?.player_id != null) aliveById.set(String(r.player_id), r.is_alive !== false);
    }
  }

  return players.map((p) => {
    const norm = (p?.breakdown_norm ?? {}) as Record<string, unknown>;
    const pid = String(p?.player_id ?? "");
    return {
      playerId: toSeatNumber(p?.player_id),
      playerName: p?.player_name ?? "",
      role: p?.role_name ?? "",
      isAlive: aliveById.has(pid) ? (aliveById.get(pid) as boolean) : true,
      gameSurvivalScore: num(norm[SCORE_DIMENSION.gameSurvivalScore]),
      logicSpeechScore: num(norm[SCORE_DIMENSION.logicSpeechScore]),
      deceptionMisleaderScore: num(norm[SCORE_DIMENSION.deceptionMisleaderScore]),
      cooperationRate: num(norm[SCORE_DIMENSION.cooperationRate]),
      totalScore: num(p?.mvp_total),
    };
  });
}

// --- vote swing ---

export function mapVoteSwing(
  data: Partial<BackendReplayPageData> | null | undefined,
): VoteSwingSpeech[] {
  const swing = scoreBlockData(data?.scores, "swing");
  const speeches = swing?.speeches;
  if (!Array.isArray(speeches)) return [];

  // speaker role/camp joined from the mvp score players (default "").
  const meta = new Map<string, { role: string; camp: string }>();
  for (const p of mvpScorePlayers(data)) {
    if (p?.player_id != null) {
      meta.set(String(p.player_id), { role: p.role_name ?? "", camp: p.camp ?? "" });
    }
  }

  return speeches.map((sp: any) => {
    const speakerId = sp?.speaker_id ?? "";
    const joined = meta.get(String(speakerId));
    const swings: VoteSwingEdge[] = Array.isArray(sp?.swings)
      ? sp.swings.map((s: any) => ({
          voter_id: s?.player_id ?? "",
          ...(s?.from_target_name != null ? { from_target: String(s.from_target_name) } : {}),
          to_target: s?.to_target_name ?? "",
        }))
      : [];
    return {
      id: `${speakerId}-${sp?.round_number ?? 0}`,
      round: num(sp?.round_number),
      speaker_id: speakerId,
      speaker_role: joined?.role ?? "",
      speaker_camp: joined?.camp ?? "",
      influence_score: num(sp?.influence_score),
      swing_count: num(sp?.swing_count),
      swings,
      before_summary: sp?.before_summary ?? "",
      after_summary: sp?.after_summary ?? "",
      public_speech: sp?.public_speech ?? "",
    };
  });
}

// --- belief matrix (god view only) ---

function rowToObserver(row: BackendBeliefRow): BeliefObserverSnapshot {
  const cells = Array.isArray(row?.first_order) ? row.first_order : [];
  const targets: BeliefTargetSnapshot[] = cells.map((c: any) => ({
    target_seat: seatLabel(c?.target_seat),
    wolf_probability: num(c?.wolf_probability), // kept 0..1 for the heatmap cell colours
    ...(c?.reason != null ? { reason: String(c.reason) } : {}),
    ...(c?.note != null ? { note: String(c.note) } : {}),
  }));
  return { observer_id: seatLabel(row?.observer_seat), targets };
}

/** Group god-view belief rows by `anchor` into the BeliefHeatmap's anchor model. */
export function mapBeliefAnchors(
  rows: BackendBeliefRow[] | null | undefined,
): BeliefAnchor[] {
  if (!Array.isArray(rows)) return [];
  const groups = new Map<string, BeliefAnchor>();
  const order: string[] = [];
  for (const row of rows) {
    const anchor = String(row?.anchor ?? "");
    let group = groups.get(anchor);
    if (!group) {
      group = {
        anchor_id: anchor,
        round: num(row?.round),
        label: `R${num(row?.round)} ${anchor}`.trim(),
        observers: [],
      };
      groups.set(anchor, group);
      order.push(anchor);
    }
    group.observers.push(rowToObserver(row));
  }
  return order.map((a) => groups.get(a) as BeliefAnchor);
}

/**
 * Group god-view belief rows by day(round) into the OTHER (types.ts) BeliefSnapshot
 * shape consumed by the ReplayPage belief column. Probabilities are scaled to 0..100.
 * Within a day the last anchor per observer wins (most recent belief state).
 */
export function mapBeliefColumns(
  rows: BackendBeliefRow[] | null | undefined,
): BeliefSnapshot[] {
  if (!Array.isArray(rows)) return [];
  const days = new Map<number, Map<number, BackendBeliefRow>>();
  const dayOrder: number[] = [];
  for (const row of rows) {
    const day = num(row?.round);
    let observers = days.get(day);
    if (!observers) {
      observers = new Map();
      days.set(day, observers);
      dayOrder.push(day);
    }
    observers.set(num(row?.observer_seat), row);
  }
  return dayOrder
    .sort((a, b) => a - b)
    .map((day) => ({
      day,
      comment: "",
      playerBeliefs: [...(days.get(day) as Map<number, BackendBeliefRow>).values()].map((row) => ({
        playerId: num(row?.observer_seat),
        playerName: seatLabel(row?.observer_seat),
        targetBeliefs: (Array.isArray(row?.first_order) ? row.first_order : []).map((c: any) => ({
          targetPlayerId: num(c?.target_seat),
          targetPlayerName: seatLabel(c?.target_seat),
          wolfProbability: Math.round(num(c?.wolf_probability) * 100),
        })),
      })),
    }));
}

/** Degraded in M2b: the front-end WolfCampSnapshot fields have no backend source. */
export function mapWolfCampSnapshots(_rows?: unknown): WolfCampSnapshot[] {
  return [];
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
    mvp_ranking: mapMvpRanking(d.mvp_ranking, mvpScorePlayers(d)),
    scores: mapPlayerScores(d),
    views_available: Array.isArray(d.views_available) ? d.views_available : [],
    report_markdown: d.report_markdown ?? "",
    coach_excerpt: d.coach_excerpt ?? "",
    belief_snapshots: mapBeliefColumns(d.belief_snapshots),
    wolf_camp_snapshots: mapWolfCampSnapshots(),
    belief_heatmap: [],
    belief_matrix_anchors: mapBeliefAnchors(d.belief_snapshots),
    vote_swing_summary: mapVoteSwing(d),
  };
}
