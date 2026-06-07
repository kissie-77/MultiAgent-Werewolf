import type { GameState, Player } from "../types";

export interface SseEvent {
  event_type: string;
  round_number?: number;
  phase?: string;
  message?: string;
  data?: Record<string, any>;
  roster?: { seat: number; name: string; role: string; camp?: string | null; is_alive?: boolean }[];
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

function seatOf(data: Record<string, any> | undefined): number | null {
  const pid = data?.player_id ?? data?.shooter_id;
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

export function initialSpectateState(): GameState {
  return {
    players: [], dayNumber: 0, phase: "START_SCREEN", currentSpeakerId: null,
    countdown: 0, speechLogs: [], narration: "", winner: null,
    wolfKilledTarget: null, witchSaved: false, witchPoisonedTarget: null,
    seerVerifiedTarget: null, seerVerificationResult: null, victimId: null,
    discussionIndex: 0, executionId: null, gameMode: "llmOnly",
  };
}

export function reduceEvent(prev: GameState, ev: SseEvent): GameState {
  const s: GameState = { ...prev, players: prev.players.map((p) => ({ ...p })), speechLogs: [...prev.speechLogs] };

  // any event carries a phase/round -> keep phase + dayNumber fresh
  if (ev.phase && PHASE_MAP[ev.phase]) s.phase = PHASE_MAP[ev.phase];
  if (typeof ev.round_number === "number" && ev.round_number > 0) s.dayNumber = ev.round_number;

  switch (ev.event_type) {
    case "snapshot": {
      if (ev.roster?.length) {
        s.players = ev.roster.map<Player>((r) => ({
          id: r.seat, name: r.name, role: r.role, isUser: false,
          isAlive: r.is_alive !== false, avatarSeed: r.name, lastSpeech: "",
          statusNotes: "",
        }));
      }
      break;
    }
    case "role_acting":
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
    case "player_speech":
    case "player_discussion": {
      const seat = seatOf(ev.data);
      const content = speechContent(ev);
      if (seat != null && content) {
        s.currentSpeakerId = seat;
        const playerName = ev.data?.player_name ?? `P${seat}`;
        upsertPlayer(s, seat, { name: playerName, lastSpeech: content });
        const p = s.players.find((x) => x.id === seat);
        s.speechLogs.push({
          playerId: seat, playerName: p?.name ?? playerName, role: p?.role ?? "",
          content, reasoning: ev.data?.reasoning,
          day: ev.round_number ?? s.dayNumber, isNight: ev.phase === "night",
        });
      }
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
    default: {
      if (ev.message) s.narration = ev.message;
    }
  }
  return s;
}
