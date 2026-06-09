import type { GameState, LiveCue, NightActionEntry, Player, SkillFx } from "../types";
import { initialLiveCue, parseThinkingContext } from "./liveCue";

/** Monotonic counter so every NightActionEntry gets a unique id for React keys. */
let nightActionId = 0;
/** Monotonic counter for SkillFx nonce. */
let skillFxNonce = 0;

export interface SseEvent {
  event_type: string;
  round_number?: number;
  phase?: string;
  message?: string;
  data?: Record<string, any>;
  roster?: { seat: number; name: string; role: string | null; camp?: string | null; is_alive?: boolean }[];
  selfSeat?: number;
  event_id?: number;
}

const PHASE_MAP: Record<string, GameState["phase"]> = {
  setup: "START_SCREEN",
  night: "NIGHT_WOLF",
  sheriff_election: "DAY_SHERIFF_RUN",
  sheriff_vote: "DAY_SHERIFF_VOTE",
  day_discussion: "DAY_DEBATE",
  day_voting: "DAY_VOTE",
  ended: "GAME_OVER",
};

const NIGHT_SUB_PHASE_TO_UI: Record<string, GameState["phase"]> = {
  pre_wolf: "NIGHT_WOLF",
  werewolf_kill: "NIGHT_WOLF",
  werewolf_chat: "NIGHT_WOLF",
  witch_decide: "NIGHT_WITCH",
  seer_check: "NIGHT_SEER",
};

function seatOf(data: Record<string, any> | undefined): number | null {
  const pid = data?.player_id ?? data?.shooter_id ?? data?.voter_id;
  if (typeof pid === "string") {
    const m = pid.match(/(\d+)$/);
    if (m) return Number(m[1]);
  }
  if (typeof data?.seat === "number") return data.seat;
  return null;
}

function upsertPlayer(s: GameState, seat: number, patch: Partial<Player>): void {
  const idx = s.players.findIndex((p) => p.id === seat);
  if (idx >= 0) {
    s.players[idx] = { ...s.players[idx], ...patch };
    return;
  }
  s.players.push({
    id: seat,
    name: patch.name ?? `P${seat}`,
    role: patch.role ?? "",
    isUser: false,
    isAlive: patch.isAlive ?? true,
    avatarSeed: patch.name ?? `P${seat}`,
    lastSpeech: patch.lastSpeech ?? "",
    statusNotes: "",
  });
}

function speechContent(ev: SseEvent): string {
  const speech = ev.data?.speech;
  if (typeof speech === "string" && speech.trim()) return speech;
  return ev.message ?? "";
}

function reasoningOf(data: Record<string, any> | undefined): string | undefined {
  const r = data?.reasoning ?? data?.private_thought;
  return typeof r === "string" && r.trim() ? r : undefined;
}

function cloneLiveCue(cue: LiveCue): LiveCue {
  return {
    thinking: cue.thinking ? { ...cue.thinking } : null,
    nightSubPhase: cue.nightSubPhase,
    nightSkill: cue.nightSkill ? { ...cue.nightSkill } : null,
    sheriffStage: cue.sheriffStage,
  };
}

function clearThinking(s: GameState): void {
  s.liveCue = { ...s.liveCue, thinking: null };
}

function setThinkingFromEvent(s: GameState, ev: SseEvent): void {
  const seat = seatOf(ev.data);
  if (seat == null) return;
  const context = parseThinkingContext(ev.data?.context);
  const selfSeat = ev.selfSeat;
  const role =
    selfSeat != null && seat !== selfSeat
      ? ""
      : String(ev.data?.role ?? s.players.find((p) => p.id === seat)?.role ?? "");
  s.liveCue = {
    ...s.liveCue,
    thinking: {
      seat,
      playerName: String(ev.data?.player_name ?? `P${seat}`),
      role,
      context,
    },
  };
  s.currentSpeakerId = null;
}

function applySpeech(
  s: GameState,
  ev: SseEvent,
  speechContext: "day" | "sheriff" | "wolf",
): void {
  const seat = seatOf(ev.data);
  const content = speechContent(ev);
  if (seat == null || !content) return;

  clearThinking(s);
  s.currentSpeakerId = seat;
  const playerName = ev.data?.player_name ?? `P${seat}`;
  upsertPlayer(s, seat, { name: playerName, lastSpeech: content });
  const p = s.players.find((x) => x.id === seat);
  const selfSeat = ev.selfSeat;
  const hidePrivate = selfSeat != null && seat !== selfSeat;
  s.speechLogs.push({
    playerId: seat,
    playerName: p?.name ?? playerName,
    role: p?.role ?? String(ev.data?.role ?? ""),
    content,
    reasoning: hidePrivate ? undefined : reasoningOf(ev.data),
    day: ev.round_number ?? s.dayNumber,
    isNight: ev.phase === "night" || speechContext === "wolf",
    speechContext,
  });
}

function applyNightSubPhase(s: GameState, name: string): void {
  s.liveCue = {
    ...s.liveCue,
    nightSubPhase: name,
    nightSkill: null,
  };
  const mapped = NIGHT_SUB_PHASE_TO_UI[name];
  if (mapped) s.phase = mapped;
}

function clearNightCues(s: GameState): void {
  s.liveCue = {
    ...s.liveCue,
    nightSubPhase: null,
    nightSkill: null,
  };
}

/** Extract the target name from event data, falling back to the raw message. */
function targetNameFromEvent(ev: SseEvent): string {
  const t = ev.data?.target_name;
  if (typeof t === "string" && t) return t;
  const tid = ev.data?.target_id;
  if (typeof tid === "string") {
    // tid may be "player_5" — strip prefix to get seat number for display.
    const m = tid.match(/(\d+)$/);
    return m ? `${m[1]}号` : tid;
  }
  if (typeof tid === "number") return `${tid}号`;
  return ev.message ?? "?";
}

/** Extract the result string from event data, converting camp to Chinese. */
function resultFromEvent(ev: SseEvent): string | null {
  const r = ev.data?.result;
  if (typeof r === "string" && r) {
    if (r === "werewolf" || r === "wolf") return "狼人";
    if (r === "human" || r === "villager") return "好人";
    return r;
  }
  return null;
}

function appendNightAction(s: GameState, ev: SseEvent): void {
  const etype = ev.event_type;
  const seat = seatOf(ev.data);
  const round = ev.round_number ?? s.dayNumber ?? 0;
  const role = (ev.data?.role ?? s.players.find((p) => p.id === seat)?.role ?? "") as string;
  const targetSeat = (() => {
    const tid = ev.data?.target_id;
    if (typeof tid === "number") return tid;
    if (typeof tid === "string") {
      const m = tid.match(/(\d+)$/);
      return m ? Number(m[1]) : null;
    }
    return null;
  })();

  const entry: NightActionEntry = {
    id: ++nightActionId,
    round,
    seat: seat ?? 0,
    role: String(role),
    actionType: etype,
    targetSeat,
    targetName: targetNameFromEvent(ev),
    result: resultFromEvent(ev),
    message: ev.message ?? "",
  };
  s.nightActionLog = [...(s.nightActionLog ?? []), entry];

  // Fire the skill-effect overlay
  s.skillFx = {
    nonce: ++skillFxNonce,
    actionType: etype,
    seat: seat ?? 0,
    role: String(role),
    targetSeat,
    targetName: targetNameFromEvent(ev),
    result: resultFromEvent(ev),
  };

  // Also update the dedicated result fields on GameState
  if (etype === "seer_checked") {
    if (targetSeat != null) s.seerVerifiedTarget = targetSeat;
    const res = ev.data?.result;
    if (res === "werewolf") s.seerVerificationResult = "WEREWOLF";
    else if (res === "human" || res === "villager") s.seerVerificationResult = "HUMAN";
  } else if (etype === "witch_saved") {
    s.witchSaved = true;
  } else if (etype === "witch_poison_used" || etype === "witch_poisoned") {
    if (targetSeat != null) s.witchPoisonedTarget = targetSeat;
  } else if (etype === "werewolf_killed") {
    if (targetSeat != null) s.wolfKilledTarget = targetSeat;
  }
}

function clearNightActions(s: GameState): void {
  s.nightActionLog = [];
}

export function initialSpectateState(): GameState {
  return {
    players: [], dayNumber: 0, phase: "START_SCREEN", currentSpeakerId: null,
    countdown: 0, speechLogs: [], eventLog: [], nightActionLog: [], narration: "", winner: null,
    wolfKilledTarget: null, witchSaved: false, witchPoisonedTarget: null,
    seerVerifiedTarget: null, seerVerificationResult: null, victimId: null,
    discussionIndex: 0, executionId: null, gameMode: "llmOnly",
    liveCue: initialLiveCue(), skillFx: null,
  };
}

export function reduceEvent(prev: GameState, ev: SseEvent): GameState {
  const s: GameState = {
    ...prev,
    players: (prev.players ?? []).map((p) => ({ ...p })),
    speechLogs: [...(prev.speechLogs ?? [])],
    eventLog: [...(prev.eventLog ?? [])],
    liveCue: cloneLiveCue(prev.liveCue ?? initialLiveCue()),
  };

  if (ev.phase && PHASE_MAP[ev.phase]) s.phase = PHASE_MAP[ev.phase];
  if (typeof ev.round_number === "number" && ev.round_number > 0) s.dayNumber = ev.round_number;

  if (ev.message) {
    const last = s.eventLog[s.eventLog.length - 1];
    if (!last || last.message !== ev.message) {
      s.eventLog.push({
        round: ev.round_number ?? s.dayNumber,
        phase: ev.phase ?? "",
        type: ev.event_type,
        message: ev.message,
      });
    }
  }

  switch (ev.event_type) {
    case "snapshot": {
      if (ev.roster?.length) {
        const selfSeat = ev.selfSeat;
        s.players = ev.roster.map<Player>((r) => ({
          id: r.seat, name: r.name, role: r.role ?? "",
          isUser: selfSeat != null && r.seat === selfSeat,
          isAlive: r.is_alive !== false, avatarSeed: r.name, lastSpeech: "",
          statusNotes: "",
        }));
      }
      break;
    }
    case "actor_thinking": {
      setThinkingFromEvent(s, ev);
      break;
    }
    case "sub_phase": {
      const name = ev.data?.name;
      if (typeof name === "string" && name) applyNightSubPhase(s, name);
      break;
    }
    case "role_acting": {
      const seat = seatOf(ev.data);
      const role = ev.data?.role;
      if (seat != null && role) {
        const selfSeat = ev.selfSeat;
        const roleText =
          selfSeat != null && seat !== selfSeat ? "" : String(role);
        upsertPlayer(s, seat, {
          name: ev.data?.player_name ?? `P${seat}`,
          role: roleText,
        });
        if (ev.data?.context === "night_skill" || ev.phase === "night") {
          clearThinking(s);
          s.liveCue = {
            ...s.liveCue,
            nightSkill: {
              seat,
              playerName: String(ev.data?.player_name ?? `P${seat}`),
              role: roleText,
              subPhase: typeof ev.data?.sub_phase === "string" ? ev.data.sub_phase : s.liveCue.nightSubPhase,
            },
          };
        }
      }
      break;
    }
    case "role_revealed": {
      const seat = seatOf(ev.data);
      const role = ev.data?.role;
      if (seat != null && role) {
        upsertPlayer(s, seat, {
          name: ev.data?.player_name ?? `P${seat}`,
          role: String(role),
        });
      }
      break;
    }
    case "player_speech": {
      applySpeech(s, ev, "day");
      break;
    }
    case "player_discussion": {
      applySpeech(s, ev, "wolf");
      break;
    }
    case "sheriff_candidate_speech": {
      s.phase = "DAY_SHERIFF_RUN";
      s.liveCue = { ...s.liveCue, sheriffStage: "campaign" };
      applySpeech(s, ev, "sheriff");
      break;
    }
    case "sheriff_campaign_started": {
      s.phase = "DAY_SHERIFF_RUN";
      s.liveCue = { ...s.liveCue, sheriffStage: "campaign" };
      if (ev.message) s.narration = ev.message;
      break;
    }
    case "game_started": {
      if (ev.message) s.narration = ev.message;
      const count = ev.data?.player_count;
      if (typeof count === "number" && count > 0 && s.players.length === 0) {
        for (let i = 1; i <= count; i += 1) {
          upsertPlayer(s, i, { name: `P${i}` });
        }
      }
      break;
    }
    case "phase_changed": {
      const phaseKey = ev.data?.phase ?? ev.phase;
      if (phaseKey && PHASE_MAP[String(phaseKey)]) {
        s.phase = PHASE_MAP[String(phaseKey)];
      }
      if (phaseKey && String(phaseKey) !== "night") {
        clearNightCues(s);
        // Keep nightActionLog so players can review actions during the day
        s.skillFx = null;
      }
      const stage = ev.data?.stage;
      if (stage === "campaign") {
        s.liveCue = { ...s.liveCue, sheriffStage: "campaign" };
      } else if (stage === "vote") {
        s.liveCue = { ...s.liveCue, sheriffStage: "vote" };
      } else if (phaseKey === "day_discussion" || phaseKey === "day_voting") {
        s.liveCue = { ...s.liveCue, sheriffStage: null };
      }
      if (ev.message) s.narration = ev.message;
      break;
    }
    case "player_died":
    case "player_eliminated": {
      const seat = seatOf(ev.data);
      if (seat != null) {
        const p = s.players.find((x) => x.id === seat);
        if (p) p.isAlive = false;
        if (ev.event_type === "player_eliminated") s.executionId = seat;
        else s.victimId = seat;
      }
      break;
    }
    case "sheriff_elected": {
      s.sheriffId = seatOf(ev.data);
      s.liveCue = { ...s.liveCue, sheriffStage: null };
      clearThinking(s);
      break;
    }
    case "game_ended": {
      s.phase = "GAME_OVER";
      const camp = ev.data?.winner_camp;
      s.winner = camp === "werewolf" ? "WOLVES" : camp === "villager" ? "VILLAGERS" : s.winner;
      clearThinking(s);
      clearNightCues(s);
      clearNightActions(s);
      s.skillFx = null;
      s.liveCue = { ...s.liveCue, sheriffStage: null };
      break;
    }
    case "game_failed": {
      s.phase = "GAME_OVER";
      s.failed = true;
      s.failureMessage = ev.message ?? "对局异常中断";
      clearThinking(s);
      clearNightCues(s);
      clearNightActions(s);
      s.skillFx = null;
      break;
    }
    // ─── Night action events — accumulate into nightActionLog ───
    case "seer_checked":
    case "witch_saved":
    case "witch_poison_used":
    case "witch_poisoned":
    case "werewolf_killed":
    case "guard_protected":
    case "lovers_linked":
    case "white_wolf_killed":
    case "wolf_beauty_charmed":
    case "nightmare_blocked":
    case "guardian_wolf_protected":
    case "raven_marked":
    case "graveyard_keeper_check":
    case "magician_swapped": {
      appendNightAction(s, ev);
      break;
    }
    default: {
      if (ev.message) s.narration = ev.message;
    }
  }
  return s;
}
