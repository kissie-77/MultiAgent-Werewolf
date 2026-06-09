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

export interface BackendHeroBlock {
  title?: string;
  subtitle?: string;
  cta_label?: string;
  cta_path?: string;
}

export interface BackendStatCard {
  label: string;
  value: number | string;
  unit?: string | null;
  hint?: string | null;
}

export interface BackendNavLink {
  key: string;
  title: string;
  path: string;
  description?: string | null;
}

export interface BackendGameMode {
  participation: string;
  rules: string;
  config_path: string;
  config_id: string;
  description: string;
  player_count: number;
}

export interface BackendHomePageData {
  hero?: BackendHeroBlock;
  nav_links?: BackendNavLink[];
  stats_cards?: BackendStatCard[];
  recent_runs?: RunSummary[];
  quick_actions?: BackendNavLink[];
  game_modes?: BackendGameMode[];
}

export interface RolePromptEntry {
  id: string;
  category: string;
  title: string;
  content: string;
  version: string;
}

export interface RoleSkillEntry {
  id: string;
  title: string;
  description: string;
  status: string;
  weight: number;
  version: string;
}

export interface RoleSummary {
  key: string;
  name: string;
  chineseName: string;
  alignment: "GOOD" | "EVIL" | "NEUTRAL";
  difficulty: "EASY" | "MEDIUM" | "HEAVY";
  tagline: string;
  shortDesc: string;
  promptCount?: number;
  skillCount?: number;
  promptVersion?: string;
  skillVersion?: string;
  promptRoleKey?: string;
  hasNightAction?: boolean;
}

export interface RoleDetail extends RoleSummary {
  lore: string;
  promptLibrary: RolePromptEntry[];
  skillLibrary: RoleSkillEntry[];
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
  victoryText?: string;
  suggestion?: string;
  boardSizes?: number[];
}

export interface RolesPageData {
  roles: RoleSummary[];
  camps?: Record<string, BackendRoleListItem[]>;
  campStats?: Record<string, number>;
  introTitle: string;
  introText: string;
  total?: number;
}

export interface BackendRoleListItem {
  key: string;
  display_name: string;
  camp: string;
  camp_label: string;
  victory_goal: string;
  has_night_action?: boolean;
  runtime_name?: string;
  prompt_role_key?: string;
  tagline?: string;
  short_desc?: string;
  difficulty?: string;
  prompt_count?: number;
  skill_count?: number;
  prompt_version?: string;
  skill_version?: string;
}

export interface BackendRolesPageData {
  title: string;
  intro_title?: string;
  intro_text?: string;
  camps: Record<string, BackendRoleListItem[]>;
  camp_stats?: Record<string, number>;
  board_presets?: unknown[];
  total: number;
}

export interface BackendRoleDetailData extends BackendRoleListItem {
  instruction?: string;
  suggestion?: string;
  victory_text?: string;
  tips?: string[];
  board_sizes?: number[];
  related_roles?: string[];
  night_action_order?: number | null;
  prompt_version?: string;
  skill_version?: string;
  prompt_library?: Array<{
    id: string;
    category: string;
    title: string;
    content: string;
    version?: string;
  }>;
  skill_library?: Array<{
    id: string;
    title: string;
    description: string;
    status?: string;
    weight?: number;
    version?: string;
  }>;
  abilities?: Array<{
    name: string;
    description: string;
    timing?: string;
  }>;
  strategies?: string[];
}

export interface BackendHowToPlayPageData {
  title: string;
  summary?: string;
  sections?: Array<{
    heading: string;
    body: string;
    bullets?: string[];
  }>;
  phase_flow?: Array<{
    order: number;
    phase_key: string;
    title: string;
    description: string;
    icon?: string;
  }>;
  victory_conditions?: Array<{
    camp: string;
    title: string;
    conditions: string[];
  }>;
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
  role_name?: string | null;
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
  model_name?: string;
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
  camp?: string;
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
    /** B1：一阶信念，观察者认为目标为狼的概率 (0-100%) */
    targetBeliefs: { targetPlayerId: number; targetPlayerName: string; wolfProbability: number }[];
    /** B2：二阶信念，观察者认为「他人怀疑自己」的程度 (0-100%) */
    secondOrderBeliefs?: { observerId: number; observerName: string; suspectsMe: number }[];
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
  /** B1：一阶信念，该观察者对每个目标的狼概率判断 */
  targets: BeliefTargetSnapshot[];
  /** B2：二阶信念，该观察者认为「目标怀疑自己」的程度 (0-1) */
  secondOrderTargets?: BeliefTargetSnapshot[];
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

export interface BackendAboutPageData {
  title: string;
  summary?: string;
  sections?: Array<{
    heading: string;
    body: string;
    bullets?: string[];
  }>;
  tech_stack?: string[];
  architecture_layers?: Array<{
    heading: string;
    body: string;
    bullets?: string[];
  }>;
  platform_stats?: Record<string, number | string>;
}

export interface AboutPageData {
  title: string;
  subtitle: string;
  description: string;
  sections: ContentSection[];
  design_principles: string[];
  roleCount?: number;
  configCount?: number;
  techStack?: string[];
  platformStats?: Record<string, number | string>;
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

// --- Game status (mirrors backend GameSnapshot / GameStatusResponse) ---
export interface GameSnapshot {
  phase: string | null;
  round_number: number;
  winner_camp: "werewolf" | "villager" | null;
  is_ended: boolean;
  sheriff_id: string | null;
  alive_count: number;
  dead_count: number;
  event_count: number;
}

export interface GameStatusResponse {
  run_id: string;
  source: string;
  status: string;
  snapshot: GameSnapshot | null;
  error: string | null;
  result_text: string | null;
  has_post_game: boolean;
  has_replay: boolean;
  post_game_status: string | null;
  alert_count: number | null;
}

// --- 复盘页面前端输入类型（镜像 models/pages.py ReplayPageData）---
// 这些描述后端 `/api/v1/pages/replay` 端点返回的原始形状。
// `replayMap.ts` 将它们映射为前端 `ReplayPageData` 形状。
export interface BackendPlayerBrief {
  player_id: string;
  player_name: string;
  role_name?: string | null;
  camp?: string | null;
  ai_model?: string | null;
  is_alive?: boolean | null;
}

export interface BackendArtifactRef {
  name: string;
  path: string;
  kind?: string;
}

export interface BackendRunDetail {
  run_id: string;
  source: string;
  path: string;
  created_at: string | null;
  player_count: number | null;
  winner_camp: string | null; // "werewolf" | "villager" | null (lowercase)
  has_post_game: boolean;
  has_replay: boolean;
  roster: BackendPlayerBrief[];
  game_result_text?: string | null;
  artifacts?: BackendArtifactRef[];
  extra?: Record<string, unknown>;
}

export interface BackendReplayEventItem {
  index: number;
  event_type: string;
  round_number: number;
  phase: string; // lowercase, e.g. "night" | "day_discussion" | "day_voting"
  message: string;
  timestamp?: string | null;
  data?: Record<string, any>;
}

export interface BackendPhaseSummary {
  round_number: number;
  phase: string;
  event_count: number;
  highlight_event_types: string[];
}

export interface BackendMvpRankItem {
  rank: number;
  player_id: string; // e.g. "player_5"
  player_name: string;
  role_name?: string | null;
  total_score: number; // KNOWN BUG: always 0.0 — real value is scores[mvp].players[].mvp_total
  ai_model?: string | null;
}

export interface BackendScoreBlock {
  kind: string; // "mvp" | "swing" | "benefit" | ...
  title: string;
  payload: { data: any };
}

export interface BackendReplayPageData {
  run: BackendRunDetail;
  view_scope?: string;
  timeline: BackendReplayEventItem[];
  phase_summary?: BackendPhaseSummary[];
  turning_points?: string[];
  mvp_ranking?: BackendMvpRankItem[];
  scores?: BackendScoreBlock[];
  views_available?: string[];
  report_markdown?: string | null;
  coach_excerpt?: string | null;
  belief_snapshots?: any[];
  wolf_camp_snapshots?: any[];
  belief_heatmap?: any;
}

// --- Models page backend INPUT type (mirror /api/v1/pages/models ModelListPageData) ---
// `modelsMap.ts` reshapes this into the front-end `ModelsPageData`: the page reads
// `usage_stats` (not `models`), `win_rate` is a 0..1 fraction (page wants a percent),
// and `avg_mvp` can be null (page calls `.toFixed`).
export interface BackendModelUsageStat {
  model_id: string;
  display_name: string;
  role_name?: string | null;
  run_count: number;
  win_rate: number | null; // 0..1 fraction, or null when no runs
  avg_mvp: number | null;
}

export interface BackendModelsPageData {
  title?: string;
  usage_stats?: BackendModelUsageStat[];
  configs?: unknown[];
  by_provider?: Record<string, unknown>;
  recommended_config_ids?: string[];
}

// --- Share replay backend INPUT type (mirror /api/v1/pages/share-replay) ---
// `shareMap.ts` reshapes this into the front-end `ShareReplayPageData`: mvp_winner
// uses snake_case (player_name/role_name) and carries no citation, winner_camp is
// lowercase ("werewolf"/"villager"), and key_moments is a list of plain strings.
export interface BackendShareReplayData {
  run_id: string;
  share_title: string;
  share_summary: string;
  winner_camp: string | null; // lowercase "werewolf" | "villager" | null
  mvp_winner: BackendMvpRankItem | null;
  key_moments?: string[];
  highlight_players?: BackendPlayerBrief[];
  stats_line: string;
}

// --- Settings API (browser -> server .env) ---
export interface ApiKeySlotStatus {
  env_name: string;
  configured: boolean;
  masked?: string | null;
}

export interface ApiKeysStatusResponse {
  keys: Record<string, ApiKeySlotStatus>;
  env_fields: Record<string, ApiKeySlotStatus>;
  env_file: string;
  writable: boolean;
}

export interface ProviderFieldSchema {
  env_name: string;
  label: string;
  required?: boolean;
  secret?: boolean;
  example?: string;
  description?: string;
}

export interface ProviderSchema {
  provider_id: string;
  display_name: string;
  fields: ProviderFieldSchema[];
}

export interface ProvidersListResponse {
  providers: ProviderSchema[];
  default_provider_id: string;
}

export interface UpdateApiKeysRequest {
  deepseek?: string;
  openai?: string;
  gemini?: string;
  claude?: string;
  doubao?: string;
  fields?: Record<string, string>;
}

export interface UpdateApiKeysResponse {
  updated_env_names: string[];
  keys: Record<string, ApiKeySlotStatus>;
  message?: string;
}

export interface AvailableModelOption {
  provider_id: string;
  provider_label: string;
  display_name: string;
}

export interface AvailableModelsResponse {
  models: AvailableModelOption[];
  default_provider_id: string;
}

// --- Start game (mirrors backend StartGameRequest / StartGameResponse) ---
export interface HumanSeatSpec {
  seat: number;
  role?: string | null;
}

export interface PlayerRosterSlot {
  provider?: string;
  name?: string;
}

export interface PlayerRosterDefaults {
  provider?: string;
}

export interface StartGameRequest {
  config_id?: string;
  participation?: string;
  rules?: string;
  player_count?: number;
  role_names?: string[];
  badge_flow?: boolean;
  human?: HumanSeatSpec;
  track_vote_intentions?: boolean;
  defaults?: PlayerRosterDefaults;
  players?: PlayerRosterSlot[];
}

export interface PlayableRoleOption {
  key: string;
  display_name: string;
  camp: string;
  camp_label: string;
}

export interface BoardPresetOption {
  preset_id: string;
  kind: string;
  title: string;
  description: string;
  tags: string[];
  player_count: number;
  role_names: string[];
  role_labels: string[];
  werewolf_count: number;
  villager_count: number;
  neutral_count: number;
}

export interface BoardPresetsResponse {
  roles: PlayableRoleOption[];
  presets: BoardPresetOption[];
  default_preset_id: string;
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
  player_token?: string | null;
  stream_path?: string | null;
  seat_page_path?: string | null;
}

// --- Human-vs-AI input bridge (mirrors backend HumanInputBroker / route) ---
// `kind` matches HumanInteractiveAgent decision kinds; `buildHumanPayload`
// (lib/humanInput.ts) folds the UI selection into the normalized `payload` text.
export type HumanInputKind = "seat" | "multi" | "yesno" | "witch" | "speech";

export interface AwaitingInputEvent {
  event_type: "awaiting_input";
  seat: number;
  request_id: string;
  kind: HumanInputKind;
  prompt: string;
  valid_targets: number[];
  deadline?: number | null;
  /** Sanitized human-facing title (browser UI). */
  title?: string;
  /** Plain-text input guidance. */
  ui_hint?: string;
  allow_skip?: boolean;
  allow_witch_save?: boolean;
  multi_count?: number;
  /** One-line human-readable question (backend-derived). */
  question?: string;
  /** The seated human's own role (engine name, e.g. "Witch"). */
  self_role?: string;
  /** For witch: the seat the wolves attacked tonight. */
  kill_target_seat?: number | null;
  /** For witch: which potions remain. */
  remaining_potions?: { save: boolean; poison: boolean } | null;
  /** Display metadata for valid_targets, so the UI can show names. */
  target_meta?: { seat: number; name: string }[];
}

export interface HumanInputRequest {
  token: string;
  request_id: string;
  kind: HumanInputKind;
  payload: string;
}

export interface HumanInputResponse {
  run_id: string;
  accepted: boolean;
  message?: string | null;
  reject_code?: string | null;
}

