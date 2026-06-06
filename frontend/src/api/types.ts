export interface HomePageData {
  title: string;
  subtitle: string;
  description: string;
  backgroundImageUrl?: string;
  welcomeMessage: string;
  stats: {
    activeGames: number;
    totalMatchesPlayed: number;
    onlineAIs: number;
    averageRating: string;
  };
  highlights: {
    id: string;
    title: string;
    summary: string;
    category: string;
    date: string;
  }[];
  quickLinks: {
    label: string;
    path: string;
    description: string;
    badge?: string;
  }[];
}

export interface RoleSummary {
  key: string;
  name: string;
  chineseName: string;
  alignment: "GOOD" | "EVIL" | "NEUTRAL";
  difficulty: "EASY" | "MEDIUM" | "HEAVY";
  tagline: string;
  shortDesc: string;
}

export interface RoleDetail extends RoleSummary {
  lore: string;
  skills: {
    name: string;
    description: string;
    timing: "NIGHT" | "DAY" | "PASSIVE";
  }[];
  strategies: string[];
  relationships: {
    targetRoleName: string;
    description: string;
    type: "ALLIED" | "THREAT" | "NEUTRAL";
  }[];
}

export interface RolesPageData {
  roles: RoleSummary[];
  introTitle: string;
  introText: string;
}

export interface ModelSummary {
  id: string;
  name: string;
  developer: string;
  rating: number; // E.g., Arena Elo
  primaryRolePreference: string;
  description: string;
  tags: string[];
}

export interface ModelDetail extends ModelSummary {
  parameters?: string;
  visionSupport: boolean;
  maxTokens: number;
  strengths: string[];
  weaknesses: string[];
  temperament: string; // E.g., "冷静偏执", "虚无诡策", "狂放冲锋"
  radarStats: {
    logic: number; // 0-100
    deception: number; // 0-100
    persuasion: number; // 0-100
    cooperation: number; // 0-100
    survivability: number; // 0-100
  };
  sampleQuote: string;
}

export interface ModelUsageStat {
  model_id: string;
  display_name: string;
  run_count: number;
  win_rate: number;
  avg_mvp: number;
}

export interface ModelsPageData {
  models: ModelUsageStat[];
  introTitle: string;
  introText: string;
}

export interface ModelComparisonData {
  models: ModelDetail[];
  dimensionAnalysis: {
    dimension: string;
    description: string;
    winnerModelId?: string;
    details: { [modelId: string]: string };
  }[];
  overallVerdict: string;
}

export interface ApiError {
  error: string;
  code?: string;
}

export interface ReplayRunInfo {
  id: string;
  date: string;
  duration: string;
  mode: string;
  speed: string;
  initial_players: number;
  user_role: string;
  winner_camp: "WOLVES" | "VILLAGERS";
}

export interface TimelineEvent {
  id: string;
  day: number;
  isNight: boolean;
  phase: string;
  title: string;
  description: string;
  keyPlayer?: string;
  actions?: string[];
  type?: 'speech' | 'kill' | 'check' | 'save' | 'vote' | 'system';
  playerId?: string;
  targetId?: string;
  result?: string;
  message?: string;
}

export interface PhaseSummary {
  phaseName: string;
  summary: string;
}

export interface TurningPoint {
  day: number;
  title: string;
  desc: string;
}

export interface MvpPlayer {
  rank: number;
  playerId: number;
  playerName: string;
  role: string;
  score: number;
  contributionDesc: string;
  isMvp: boolean;
}

export interface PlayerScore {
  playerId: number;
  playerName: string;
  role: string;
  isAlive: boolean;
  gameSurvivalScore: number;
  logicSpeechScore: number;
  deceptionMisleaderScore: number;
  cooperationRate: number;
  totalScore: number;
}

export interface BeliefSnapshot {
  day: number;
  comment: string;
  playerBeliefs: {
    playerId: number;
    playerName: string;
    targetBeliefs: { targetPlayerId: number; targetPlayerName: string; wolfProbability: number }[]; // 0-100%
  }[];
}

export interface WolfCampSnapshot {
  day: number;
  campStrategy: string;
  targetSelectionId: number;
  targetSelectionName: string;
  wolfVotes: { wolfPlayerId: number; wolfPlayerName: string; votedForId: number; votedForName: string }[];
}

export interface HeatmapCell {
  rowPlayerId: number;
  rowPlayerName: string;
  colPlayerId: number;
  colPlayerName: string;
  distrustLevel: number; // 0-100 indicating distrust
}

export interface BeliefAnchor {
  anchor_id: string; // e.g. "R1_START", "R1_VOTE"
  round: number;
  label: string;
  observers: BeliefObserverSnapshot[];
}

export interface BeliefObserverSnapshot {
  observer_id: string; // e.g. "P1"
  targets: BeliefTargetSnapshot[];
}

export interface BeliefTargetSnapshot {
  target_seat: string; // "P1", "P2"
  wolf_probability: number; // 0.0 - 1.0
  reason?: string;
  note?: string;
}

export interface VoteSwingSpeech {
  id: string;
  round: number;
  speaker_id: string;
  speaker_role: string;
  speaker_camp: string;
  influence_score: number;
  swing_count: number;
  swings: VoteSwingEdge[];
  before_summary: string;
  after_summary: string;
  public_speech: string;
}

export interface VoteSwingEdge {
  voter_id: string;
  from_target?: string;
  to_target: string;
}

export interface ReplayPageData {
  run: ReplayRunInfo;
  timeline: TimelineEvent[];
  phase_summary: PhaseSummary[];
  turning_points: TurningPoint[];
  mvp_ranking: MvpPlayer[];
  scores: PlayerScore[];
  views_available: string[];
  report_markdown: string;
  coach_excerpt: string;
  belief_snapshots: BeliefSnapshot[];
  wolf_camp_snapshots: WolfCampSnapshot[];
  belief_heatmap: HeatmapCell[];
  belief_matrix_anchors: BeliefAnchor[];
  vote_swing_summary: VoteSwingSpeech[];
}

export interface ShareReplayPageData {
  share_title: string;
  share_summary: string;
  winner_camp: "WOLVES" | "VILLAGERS";
  mvp_winner: {
    playerName: string;
    playerId: number;
    role: string;
    citation: string;
  };
  key_moments: {
    timeLabel: string;
    desc: string;
  }[];
  highlight_players: {
    playerName: string;
    role: string;
    badge: string;
    description: string;
  }[];
  stats_line: string;
}

export interface ContentSection {
  title: string;
  value: string;
}

export interface AboutPageData {
  title: string;
  subtitle: string;
  description: string;
  sections: ContentSection[];
  design_principles: string[];
}

export interface FeatureCard {
  title: string;
  description: string;
  icon: string;
  value_stat?: string;
  badge?: string;
}

export interface FeaturesPageData {
  title: string;
  subtitle: string;
  description: string;
  sections: ContentSection[];
  feature_cards: FeatureCard[];
}

export interface VictoryCondition {
  camp: string;
  title: string;
  conditions: string[];
}

export interface PhaseFlowItem {
  phase: string;
  description: string;
  duration_hint: string;
}

export interface HowToPlayPageData {
  title: string;
  subtitle: string;
  description: string;
  sections: ContentSection[];
  phase_flow: PhaseFlowItem[];
  victory_conditions: VictoryCondition[];
}

export interface NightStep {
  seq: number;
  title: string;
  description: string;
}

export interface InvolvedRole {
  name: string;
  action_description: string;
}

export interface VisibilityRule {
  title: string;
  rule: string;
}

export interface NightPhasePageData {
  title: string;
  subtitle: string;
  description: string;
  sections: ContentSection[];
  steps: NightStep[];
  involved_roles: InvolvedRole[];
  visibility_rules: VisibilityRule[];
  timeout_hints: string[];
}

export interface PhaseTip {
  phase: string;
  tips: string[];
}

export interface RoleTip {
  role: string;
  tips: string[];
}

export interface RoleTipByCamp {
  camp: string;
  tips: string[];
}

export interface StrategyPageData {
  title: string;
  subtitle: string;
  description: string;
  sections: ContentSection[];
  general_tips: string[];
  phase_tips: PhaseTip[];
  role_tips: RoleTip[];
  role_tips_by_camp: RoleTipByCamp[];
}

// --- Runs list (mirrors backend ApiResponse[RunListPageData]) ---
export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface Paginated<T> {
  items: T[];
  meta: PageMeta;
}

export interface RunSummary {
  run_id: string;
  source: string; // "runs" | "eval"
  path: string;
  created_at: string | null;
  player_count: number | null;
  winner_camp: string | null; // "GOOD" | "WEREWOLF" | ... | null
  has_post_game: boolean;
  has_replay: boolean;
}

export interface RunListPageData {
  runs: Paginated<RunSummary>;
}

// --- Start game (mirrors backend StartGameRequest / StartGameResponse) ---
export interface StartGameRequest {
  config_id?: string;
  participation?: string;
  rules?: string;
  player_count?: number;
  badge_flow?: boolean;
}

export interface StartGameResponse {
  run_id: string;
  source: string;
  status: string;
  config_id: string;
  run_dir: string;
  game_page_path: string;
  status_path: string;
  replay_page_path: string;
  player_count?: number | null;
  badge_flow?: boolean;
}

