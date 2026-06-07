import type { GameState, Player } from "../types";

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
  day_discussion: "DAY_DEBATE",
  day_voting: "DAY_VOTE",
  ended: "GAME_OVER",
};

function seatOf(data: Record<string, any> | undefined): number | null {
  const pid = data?.player_id;
  if (typeof pid === "string") {
    const m = pid.match(/(\d+)$/);
    if (m) return Number(m[1]);
  }
  if (typeof data?.seat === "number") return data.seat;
  return null;
}

export function initialSpectateState(): GameState {
  return {
    players: [], dayNumber: 0, phase: "START_SCREEN", currentSpeakerId: null,
    countdown: 0, speechLogs: [], eventLog: [], narration: "", winner: null,
    wolfKilledTarget: null, witchSaved: false, witchPoisonedTarget: null,
    seerVerifiedTarget: null, seerVerificationResult: null, victimId: null,
    discussionIndex: 0, executionId: null, gameMode: "llmOnly",
  };
}

export function reduceEvent(prev: GameState, ev: SseEvent): GameState {
  const s: GameState = { ...prev, players: (prev.players ?? []).map((p) => ({ ...p })), speechLogs: [...(prev.speechLogs ?? [])], eventLog: [...(prev.eventLog ?? [])] };

  // any event carries a phase/round -> keep phase + dayNumber fresh
  if (ev.phase && PHASE_MAP[ev.phase]) s.phase = PHASE_MAP[ev.phase];
  if (typeof ev.round_number === "number" && ev.round_number > 0) s.dayNumber = ev.round_number;

  // accumulate every messaged event into a chronological timeline (dedupe adjacent repeats)
  if (ev.message) {
    const last = s.eventLog[s.eventLog.length - 1];
    if (!last || last.message !== ev.message) {
      s.eventLog.push({ round: ev.round_number ?? s.dayNumber, phase: ev.phase ?? "", type: ev.event_type, message: ev.message });
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
    case "player_speech":
    case "player_discussion":
    case "sheriff_candidate_speech": {
      const seat = seatOf(ev.data);
      if (seat != null) {
        s.currentSpeakerId = seat;
        const p = s.players.find((x) => x.id === seat);
        if (p) p.lastSpeech = ev.message ?? "";
        s.speechLogs.push({
          playerId: seat, playerName: p?.name ?? `P${seat}`, role: p?.role ?? "",
          content: ev.message ?? "", reasoning: ev.data?.reasoning,
          day: ev.round_number ?? s.dayNumber, isNight: ev.phase === "night",
        });
      }
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
      break;
    }
    case "game_ended": {
      s.phase = "GAME_OVER";
      const camp = ev.data?.winner_camp;
      s.winner = camp === "werewolf" ? "WOLVES" : camp === "villager" ? "VILLAGERS" : s.winner;
      break;
    }
    case "game_failed": {
      // Backend crashed mid-run (e.g. sheriff-election LLM timeout). Surface a
      // clear interrupted state instead of leaving the UI frozen on the last phase.
      s.phase = "GAME_OVER";
      s.failed = true;
      s.failureMessage = ev.message ?? "对局异常中断";
      break;
    }
    default: {
      if (ev.message) s.narration = ev.message;
    }
  }
  return s;
}
