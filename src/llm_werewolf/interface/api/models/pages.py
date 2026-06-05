"""Page-specific response schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, BaseModel

if TYPE_CHECKING:
    from llm_werewolf.interface.api.models.common import (
        NavLink,
        RunDetail,
        RunSummary,
        ArtifactRef,
        PlayerBrief,
        PaginatedList,
    )

# --- Shared UI blocks ---


class HeroBlock(BaseModel):
    title: str
    subtitle: str
    cta_label: str = "开始对局"
    cta_path: str = "/game"


class StatCard(BaseModel):
    label: str
    value: int | str
    unit: str | None = None
    hint: str | None = None


class FeatureCard(BaseModel):
    key: str
    title: str
    description: str
    icon: str | None = None
    bullets: list[str] = Field(default_factory=list)


class PhaseFlowStep(BaseModel):
    order: int
    phase_key: str
    title: str
    description: str
    icon: str | None = None


class BoardPreset(BaseModel):
    player_count: int
    role_names: list[str]
    werewolf_count: int
    villager_count: int
    neutral_count: int = 0
    timeouts: dict[str, int] = Field(default_factory=dict)


class GameSnapshot(BaseModel):
    phase: str | None = None
    round_number: int = 0
    winner_camp: str | None = None
    is_ended: bool = False
    sheriff_id: str | None = None
    alive_count: int = 0
    dead_count: int = 0
    event_count: int = 0


class PhaseSummary(BaseModel):
    round_number: int
    phase: str
    event_count: int
    highlight_event_types: list[str] = Field(default_factory=list)


class MvpRankItem(BaseModel):
    rank: int
    player_id: str
    player_name: str
    role_name: str | None = None
    total_score: float = 0.0
    ai_model: str | None = None


class ModelPlayerSlot(BaseModel):
    seat: int
    name: str
    model: str
    plan: str | None = None
    reasoning_effort: str | None = None


# --- Entry / Home ---


class HomePageData(BaseModel):
    hero: HeroBlock
    nav_links: list[NavLink]
    stats_cards: list[StatCard]
    recent_runs: list[RunSummary]
    quick_actions: list[NavLink]
    game_modes: list[GameModeOption] = Field(default_factory=list)


# --- Content pages (intro / guide) ---


class ContentSection(BaseModel):
    heading: str
    body: str
    bullets: list[str] = Field(default_factory=list)


class ContentPageData(BaseModel):
    page_key: str
    title: str
    summary: str
    sections: list[ContentSection] = Field(default_factory=list)
    related_links: list[NavLink] = Field(default_factory=list)


class AboutPageData(ContentPageData):
    tech_stack: list[str] = Field(default_factory=list)
    architecture_layers: list[ContentSection] = Field(default_factory=list)
    platform_stats: dict[str, int | str] = Field(default_factory=dict)


class FeaturesPageData(ContentPageData):
    feature_cards: list[FeatureCard] = Field(default_factory=list)


class HowToPlayPageData(ContentPageData):
    phase_flow: list[PhaseFlowStep] = Field(default_factory=list)
    victory_conditions: list[ContentSection] = Field(default_factory=list)


class NightPhaseStep(BaseModel):
    order: int
    role_group: str
    title: str
    description: str


class NightPhasePageData(ContentPageData):
    steps: list[NightPhaseStep] = Field(default_factory=list)
    involved_roles: dict[str, list[str]] = Field(default_factory=dict)
    visibility_rules: list[ContentSection] = Field(default_factory=list)
    timeout_hints: dict[str, int] = Field(default_factory=dict)


# --- Roles ---


class RoleListItem(BaseModel):
    key: str
    display_name: str
    camp: str
    camp_label: str
    victory_goal: str
    has_night_action: bool = False


class RoleDetail(RoleListItem):
    runtime_name: str
    instruction: str
    suggestion: str
    victory_text: str
    tips: list[str] = Field(default_factory=list)


class RoleDetailPageData(RoleDetail):
    board_sizes: list[int] = Field(default_factory=list)
    related_roles: list[str] = Field(default_factory=list)
    night_action_order: int | None = None


class RoleListPageData(BaseModel):
    title: str
    camps: dict[str, list[RoleListItem]]
    camp_stats: dict[str, int] = Field(default_factory=dict)
    board_presets: list[BoardPreset] = Field(default_factory=list)
    total: int


# --- AI Models ---


class ModelConfigBrief(BaseModel):
    config_id: str
    config_path: str
    label: str
    provider: str | None = None
    player_count: int
    models: list[str]
    agent_backend: str | None = None
    language: str | None = None


class ModelUsageStat(BaseModel):
    model_id: str
    display_name: str
    run_count: int = 0
    win_rate: float | None = None
    avg_mvp: float | None = None


class ModelListPageData(BaseModel):
    title: str
    configs: list[ModelConfigBrief]
    by_provider: dict[str, list[ModelConfigBrief]] = Field(default_factory=dict)
    usage_stats: list[ModelUsageStat] = Field(default_factory=list)
    recommended_config_ids: list[str] = Field(default_factory=list)


class ModelDetailPageData(BaseModel):
    model_id: str
    display_name: str
    configs: list[ModelConfigBrief]
    usage: ModelUsageStat | None = None
    player_slots: list[ModelPlayerSlot] = Field(default_factory=list)
    compare_with: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ModelCompareItem(BaseModel):
    model_id: str
    display_name: str
    run_count: int
    win_rate: float | None = None
    avg_mvp: float | None = None


class ModelComparePageData(BaseModel):
    models: list[ModelCompareItem]
    metric_labels: dict[str, str] = Field(default_factory=dict)


# --- Game / Replay ---


class GameModeOption(BaseModel):
    participation: str
    rules: str
    config_path: str
    config_id: str | None = None
    description: str
    player_count: int | None = None


class GamePageData(BaseModel):
    title: str
    modes: list[GameModeOption]
    active_run: RunDetail | None = None
    snapshot: GameSnapshot | None = None
    board_preset: BoardPreset | None = None
    players: list[PlayerBrief] = Field(default_factory=list)
    camp_counts: dict[str, int] = Field(default_factory=dict)
    recent_events: list[ReplayEventItem] = Field(default_factory=list)


class ReplayEventItem(BaseModel):
    index: int
    event_type: str
    round_number: int
    phase: str
    message: str
    timestamp: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ReplayScoreBlock(BaseModel):
    kind: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ReplayPageData(BaseModel):
    run: RunDetail
    view_scope: str = "public"
    timeline: list[ReplayEventItem]
    phase_summary: list[PhaseSummary] = Field(default_factory=list)
    turning_points: list[str] = Field(default_factory=list)
    mvp_ranking: list[MvpRankItem] = Field(default_factory=list)
    scores: list[ReplayScoreBlock] = Field(default_factory=list)
    views_available: list[str] = Field(default_factory=list)
    report_markdown: str | None = None
    coach_excerpt: str | None = None
    belief_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    wolf_camp_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    belief_heatmap: dict[str, Any] = Field(default_factory=dict)


class ShareReplayPageData(BaseModel):
    run_id: str
    share_title: str
    share_summary: str
    og_title: str
    og_description: str
    winner_camp: str | None = None
    mvp_winner: MvpRankItem | None = None
    key_moments: list[str] = Field(default_factory=list)
    highlight_players: list[PlayerBrief] = Field(default_factory=list)
    share_url_path: str
    og_image_path: str | None = None
    stats_line: str = ""
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class StrategyTip(BaseModel):
    role_key: str | None
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)


class StrategyPageData(BaseModel):
    title: str
    general_tips: list[StrategyTip]
    phase_tips: list[StrategyTip] = Field(default_factory=list)
    role_tips: list[StrategyTip]
    role_tips_by_camp: dict[str, list[StrategyTip]] = Field(default_factory=dict)
    post_game_links: list[NavLink] = Field(default_factory=list)


class RunListPageData(BaseModel):
    runs: PaginatedList[RunSummary]
