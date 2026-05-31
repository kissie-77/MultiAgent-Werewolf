export interface Player {
  id: number;
  name: string;
  role: "预言家" | "女巫" | "猎人" | "狼人" | "村民";
  isUser: boolean;
  isAlive: boolean;
  avatarSeed: string;
  lastSpeech: string;
  statusNotes: string;
  votedFor?: number;
}

export interface GameState {
  players: Player[];
  dayNumber: number;
  phase: "START_SCREEN" | "ROLE_CHOICE" | "NIGHT_WOLF" | "NIGHT_SEER" | "NIGHT_WITCH" | "DAY_ANNOUNCEMENT" | "DAY_DEBATE" | "DAY_VOTE" | "GAME_OVER";
  currentSpeakerId: number | null;
  countdown: number;
  speechLogs: { playerId: number; playerName: string; role: string; content: string; day: number; isNight: boolean }[];
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
}
