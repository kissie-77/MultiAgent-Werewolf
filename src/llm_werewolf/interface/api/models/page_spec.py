"""Per-page field specifications for frontend integration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PageFieldSpec(BaseModel):
    """Describes one data field a frontend page consumes."""

    name: str
    type: str
    description: str
    required: bool = True
    example: str | None = None


class PageSpec(BaseModel):
    page_key: str
    frontend_route: str
    api_path: str
    title: str
    description: str
    query_params: list[str] = Field(default_factory=list)
    fields: list[PageFieldSpec]


PAGE_SPECS: dict[str, PageSpec] = {
    "home": PageSpec(
        page_key="home",
        frontend_route="/",
        api_path="/api/v1/pages/home",
        title="进入页",
        description="首页：导航、统计卡片、最近对局、快捷入口",
        fields=[
            PageFieldSpec(name="hero", type="HeroBlock", description="主标题与副标题"),
            PageFieldSpec(name="stats_cards", type="StatCard[]", description="平台统计数字"),
            PageFieldSpec(name="nav_links", type="NavLink[]", description="全站导航"),
            PageFieldSpec(name="recent_runs", type="RunSummary[]", description="最近 8 局"),
            PageFieldSpec(name="quick_actions", type="NavLink[]", description="快捷 CTA"),
            PageFieldSpec(name="game_modes", type="GameModeOption[]", description="可开局模式"),
        ],
    ),
    "game": PageSpec(
        page_key="game",
        frontend_route="/game",
        api_path="/api/v1/pages/game",
        title="主游戏页",
        description="观战/回放主界面：模式选择 + 对局快照 + 玩家列表 + 最近事件",
        query_params=["run_id", "source", "config_id"],
        fields=[
            PageFieldSpec(name="modes", type="GameModeOption[]", description="可选开局配置"),
            PageFieldSpec(name="snapshot", type="GameSnapshot", description="当前局阶段/回合", required=False),
            PageFieldSpec(name="players", type="PlayerBrief[]", description="玩家 roster"),
            PageFieldSpec(name="camp_counts", type="dict", description="阵营存活统计"),
            PageFieldSpec(name="recent_events", type="ReplayEventItem[]", description="最近 20 条事件"),
            PageFieldSpec(name="board_preset", type="BoardPreset", description="板子角色构成", required=False),
        ],
    ),
    "about": PageSpec(
        page_key="about",
        frontend_route="/about",
        api_path="/api/v1/pages/about",
        title="AI 狼人杀介绍",
        description="项目定位、技术栈、架构分层、平台数据",
        fields=[
            PageFieldSpec(name="sections", type="ContentSection[]", description="正文段落"),
            PageFieldSpec(name="tech_stack", type="string[]", description="技术栈标签"),
            PageFieldSpec(name="architecture_layers", type="ContentSection[]", description="架构分层"),
            PageFieldSpec(name="platform_stats", type="dict", description="角色数/配置数等"),
        ],
    ),
    "features": PageSpec(
        page_key="features",
        frontend_route="/features",
        api_path="/api/v1/pages/features",
        title="功能介绍",
        description="功能卡片列表，含子能力 bullet",
        fields=[
            PageFieldSpec(name="feature_cards", type="FeatureCard[]", description="功能卡片"),
            PageFieldSpec(name="sections", type="ContentSection[]", description="补充说明"),
        ],
    ),
    "how-to-play": PageSpec(
        page_key="how-to-play",
        frontend_route="/how-to-play",
        api_path="/api/v1/pages/how-to-play",
        title="玩法说明",
        description="阶段流程、胜利条件、投票/警长规则",
        fields=[
            PageFieldSpec(name="phase_flow", type="PhaseFlowStep[]", description="日/夜循环步骤"),
            PageFieldSpec(name="victory_conditions", type="ContentSection[]", description="胜负条件"),
            PageFieldSpec(name="sections", type="ContentSection[]", description="平台操作说明"),
        ],
    ),
    "night-phase": PageSpec(
        page_key="night-phase",
        frontend_route="/night-phase",
        api_path="/api/v1/pages/night-phase",
        title="夜晚阶段介绍",
        description="夜间行动顺序、涉及角色、可见性规则、超时参考",
        fields=[
            PageFieldSpec(name="steps", type="NightPhaseStep[]", description="行动顺序"),
            PageFieldSpec(name="involved_roles", type="dict", description="每步涉及角色 key"),
            PageFieldSpec(name="visibility_rules", type="ContentSection[]", description="信息隔离规则"),
            PageFieldSpec(name="timeout_hints", type="dict", description="night/day/vote 秒数参考"),
        ],
    ),
    "replay": PageSpec(
        page_key="replay",
        frontend_route="/replay/{run_id}",
        api_path="/api/v1/pages/replay",
        title="本局复盘",
        description="完整时间线、评分、转折点、MVP 榜、报告",
        query_params=["run_id", "source"],
        fields=[
            PageFieldSpec(name="run", type="RunDetail", description="对局元数据"),
            PageFieldSpec(name="timeline", type="ReplayEventItem[]", description="事件时间线"),
            PageFieldSpec(name="phase_summary", type="PhaseSummary[]", description="按回合/阶段汇总"),
            PageFieldSpec(name="turning_points", type="string[]", description="关键转折"),
            PageFieldSpec(name="mvp_ranking", type="MvpRankItem[]", description="MVP 排行"),
            PageFieldSpec(name="scores", type="ReplayScoreBlock[]", description="赛后评分块"),
            PageFieldSpec(name="report_markdown", type="string", required=False, description="LLM/质量报告"),
        ],
    ),
    "share-replay": PageSpec(
        page_key="share-replay",
        frontend_route="/share/replay/{run_id}",
        api_path="/api/v1/pages/share-replay",
        title="分享复盘",
        description="社交分享摘要、OG 文案、高光玩家",
        query_params=["run_id", "source"],
        fields=[
            PageFieldSpec(name="share_title", type="string", description="分享标题"),
            PageFieldSpec(name="share_summary", type="string", description="分享摘要"),
            PageFieldSpec(name="og_title", type="string", description="OpenGraph 标题"),
            PageFieldSpec(name="og_description", type="string", description="OpenGraph 描述"),
            PageFieldSpec(name="mvp_winner", type="PlayerBrief", required=False, description="MVP 玩家"),
            PageFieldSpec(name="key_moments", type="string[]", description="3 条关键瞬间"),
        ],
    ),
    "strategy": PageSpec(
        page_key="strategy",
        frontend_route="/strategy",
        api_path="/api/v1/pages/strategy",
        title="攻略",
        description="通用/分角色/分阶段攻略",
        fields=[
            PageFieldSpec(name="general_tips", type="StrategyTip[]", description="通用攻略"),
            PageFieldSpec(name="phase_tips", type="StrategyTip[]", description="按阶段分组"),
            PageFieldSpec(name="role_tips", type="StrategyTip[]", description="按角色分组"),
            PageFieldSpec(name="role_tips_by_camp", type="dict", description="按阵营分组"),
        ],
    ),
    "roles": PageSpec(
        page_key="roles",
        frontend_route="/roles",
        api_path="/api/v1/pages/roles",
        title="角色列表",
        description="22 角色按阵营分组 + 板子预设",
        fields=[
            PageFieldSpec(name="camps", type="dict[str, RoleListItem[]]", description="按阵营分组的角色列表"),
            PageFieldSpec(name="camp_stats", type="dict", description="各阵营数量"),
            PageFieldSpec(name="board_presets", type="BoardPreset[]", description="6–20 人板子"),
        ],
    ),
    "role-detail": PageSpec(
        page_key="role-detail",
        frontend_route="/roles/{role_key}",
        api_path="/api/v1/pages/roles/{role_key}",
        title="角色详情",
        description="技能、策略、出现板子、关联角色",
        query_params=["role_key"],
        fields=[
            PageFieldSpec(name="instruction", type="string", description="技能说明"),
            PageFieldSpec(name="suggestion", type="string", description="策略建议"),
            PageFieldSpec(name="board_sizes", type="int[]", description="出现在哪些人数板"),
            PageFieldSpec(name="night_action_order", type="int", required=False, description="夜间行动顺序序号"),
            PageFieldSpec(name="related_roles", type="string[]", description="关联角色 key 列表"),
        ],
    ),
    "models": PageSpec(
        page_key="models",
        frontend_route="/models",
        api_path="/api/v1/pages/models",
        title="AI 模型列表",
        description="配置文件、提供商分组、历史用量",
        fields=[
            PageFieldSpec(name="configs", type="ModelConfigBrief[]", description="可用模型配置列表"),
            PageFieldSpec(name="by_provider", type="dict", description="按 provider 分组"),
            PageFieldSpec(name="usage_stats", type="ModelUsageStat[]", description="历史用量统计"),
            PageFieldSpec(name="recommended_config_ids", type="string[]", description="推荐配置 ID"),
        ],
    ),
    "model-detail": PageSpec(
        page_key="model-detail",
        frontend_route="/models/{model_id}",
        api_path="/api/v1/pages/models/{model_id}",
        title="模型详情",
        description="关联配置、历史表现、可对比模型",
        query_params=["model_id"],
        fields=[
            PageFieldSpec(name="configs", type="ModelConfigBrief[]", description="关联配置"),
            PageFieldSpec(name="usage", type="ModelUsageStat", required=False, description="该模型历史表现"),
            PageFieldSpec(name="player_slots", type="ModelPlayerSlot[]", description="各座位模型配置"),
            PageFieldSpec(name="compare_with", type="string[]", description="可对比的其他模型 ID"),
        ],
    ),
    "model-compare": PageSpec(
        page_key="model-compare",
        frontend_route="/models/compare",
        api_path="/api/v1/pages/models/compare",
        title="模型对比",
        description="多模型指标并排对比",
        query_params=["ids"],
        fields=[
            PageFieldSpec(name="models", type="ModelCompareItem[]", description="对比模型列表"),
            PageFieldSpec(name="metric_labels", type="dict", description="指标名称映射"),
        ],
    ),
}


def list_page_specs() -> list[PageSpec]:
    return list(PAGE_SPECS.values())


def get_page_spec(page_key: str) -> PageSpec | None:
    return PAGE_SPECS.get(page_key)
