/** Context for `LiveCue.thinking` — maps 1:1 to backend `actor_thinking.data.context`. */
export type ThinkingContext =
  | "day_speech"
  | "sheriff_speech"
  | "sheriff_vote"
  | "werewolf_chat"
  | "night_skill"
  | "general";

/**
 * Real-time UI cues for animators. Updated by SSE/log reducer only.
 * - `thinking`: non-null ONLY while an actor is waiting on LLM/human input
 * - `nightSkill`: placeholder while a role performs a night action (god view / own seat)
 * - `nightSubPhase`: coarse night timeline step from backend `sub_phase`
 */
export interface LiveCue {
  thinking: {
    seat: number;
    playerName: string;
    role: string;
    context: ThinkingContext;
  } | null;
  nightSubPhase: string | null;
  nightSkill: {
    seat: number;
    playerName: string;
    role: string;
    subPhase: string | null;
  } | null;
  sheriffStage: "campaign" | "vote" | null;
}

export interface Player {
  id: number;
  name: string;
  role: string;
  isUser: boolean;
  isAlive: boolean;
  avatarSeed: string;
  lastSpeech: string;
  lastReasoning?: string;
  statusNotes: string;
  votedFor?: number;
}

/** A single night action record — displayed in the NightActionLog component. */
export interface NightActionEntry {
  /** Monotonic id for React keys / animation. */
  id: number;
  /** Which night round this action belongs to. */
  round: number;
  /** The actor's seat. */
  seat: number;
  /** The actor's role name in Chinese (e.g. "预言家", "女巫", "狼人"). */
  role: string;
  /** SSE event_type string (e.g. "seer_checked", "werewolf_killed"). */
  actionType: string;
  /** Target seat, or null when the event doesn't have a single target. */
  targetSeat: number | null;
  /** Human-readable target name. */
  targetName: string;
  /** Optional result string (e.g. "好人" / "狼人" for seer checks). */
  result: string | null;
  /** Raw message from the backend (with emoji prefix). */
  message: string;
}

/** A transient skill-effect overlay triggered when a night action result arrives. */
export interface SkillFx {
  /** Monotonic nonce so React treats each occurrence as a new animation. */
  nonce: number;
  /** SSE event_type (e.g. "seer_checked", "werewolf_killed"). */
  actionType: string;
  /** Actor's seat number. */
  seat: number;
  /** Actor's role name in Chinese. */
  role: string;
  /** Target seat, or null. */
  targetSeat: number | null;
  /** Human-readable target name. */
  targetName: string;
  /** Optional result (e.g. "好人" / "狼人" for seer). */
  result: string | null;
}

export interface GameState {
  players: Player[];
  dayNumber: number;
  phase: "START_SCREEN" | "ROLE_CHOICE" | "NIGHT_WOLF" | "NIGHT_SEER" | "NIGHT_WITCH" | "DAY_SHERIFF_RUN" | "DAY_SHERIFF_VOTE" | "DAY_ANNOUNCEMENT" | "DAY_DEBATE" | "DAY_VOTE" | "GAME_OVER";
  currentSpeakerId: number | null;
  countdown: number;
  speechLogs: {
    playerId: number;
    playerName: string;
    role: string;
    content: string;
    reasoning?: string;
    day: number;
    isNight: boolean;
    /** Distinguishes sheriff campaign speeches from ordinary day debate. */
    speechContext?: "day" | "sheriff" | "wolf";
  }[];
  eventLog: { round: number; phase: string; type: string; message: string }[];
  /** Night action entries accumulated during the night, cleared when day breaks. */
  nightActionLog: NightActionEntry[];
  /** Animation hooks — see `LiveCue` JSDoc. */
  liveCue: LiveCue;
  narration: string;
  winner: "WOLVES" | "VILLAGERS" | null;
  wolfKilledTarget: number | null;
  witchSaved: boolean;
  witchPoisonedTarget: number | null;
  seerVerifiedTarget: number | null;
  seerVerificationResult: "HUMAN" | "WEREWOLF" | null;
  victimId: number | null;
  discussionIndex: number;
  executionId: number | null;
  gameMode?: "llmOnly" | "humanVsAI";
  playerCount?: number;
  hasSheriff?: boolean;
  sheriffId?: number | null;
  sheriffCandidates?: number[];
  /** Transient skill-effect signal from the reducer. NightSkillOverlay was retired
   * in favor of the tarot CastSkillOverlay (store.activeCast); currently unconsumed. */
  skillFx: SkillFx | null;
  /** Set when the backend reports the run crashed (game_failed SSE event). */
  failed?: boolean;
  failureMessage?: string;
}

/** Skill-cast effect category — drives the tarot overlay theme + SFX. */
export type EffectType =
  | "inspect" | "heal" | "poison" | "bite" | "shoot" | "vote" | "rally"
  | "guard" | "charm" | "mark" | "link" | "duel" | "swap" | "corpse" | "fear";

/** A transient skill-cast cinematic signal consumed by CastSkillOverlay. */
export interface ActiveCast {
  casterId: number | "USER";
  casterName: string;
  role: string;
  skillName: string;
  skillSub: string;
  targetId: number | null;
  targetName: string | null;
  /** Action verb for the caster→target line, e.g. "击杀" / "查验" ("" when no target). */
  targetVerb: string;
  effectType: EffectType;
}
