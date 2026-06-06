"""Assemble complete page payloads for frontend."""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.game_runtime.roles.catalog import get_catalog, get_definition
from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.api.models.pages import (
    StatCard,
    HeroBlock,
    BoardPreset,
    FeatureCard,
    StrategyTip,
    GamePageData,
    HomePageData,
    AboutPageData,
    PhaseFlowStep,
    GameModeOption,
    ReplayPageData,
    ModelPlayerSlot,
    FeaturesPageData,
    RoleListPageData,
    StrategyPageData,
    HowToPlayPageData,
    ModelListPageData,
    NightPhasePageData,
    RoleDetailPageData,
    ModelDetailPageData,
    ShareReplayPageData,
)
from llm_werewolf.interface.api.services.runs import (
    list_run_dirs,
    get_run_detail,
    aggregate_model_usage,
)
from llm_werewolf.interface.cli.runtime.modes import list_modes
from llm_werewolf.interface.api.services.board import build_board_presets, board_sizes_for_role
from llm_werewolf.interface.api.services.config import (
    get_model_detail,
    list_models_page,
    list_config_files,
    parse_config_brief,
)
from llm_werewolf.interface.api.services.replay import (
    _load_json,
    recent_events,
    get_replay_page,
    build_mvp_ranking,
    build_phase_summary,
    extract_camp_counts,
    extract_game_snapshot,
    get_share_replay_page,
    build_turning_point_lines,
)
from llm_werewolf.interface.api.services.catalog import get_role_detail, list_roles_page
from llm_werewolf.interface.api.services.content import (
    CAMP_LABELS,
    get_about_page,
    get_home_content,
    default_nav_links,
    get_features_page,
    get_strategy_page,
    get_how_to_play_page,
    get_night_phase_page,
)

_NIGHT_STEP_ROLES = {
    "pre_wolf": ["Cupid", "NightmareWolf", "Guard", "GuardianWolf", "Thief"],
    "wolf_discussion": ["Werewolf", "AlphaWolf", "HiddenWolf", "WhiteWolf"],
    "wolf_vote": ["Werewolf", "AlphaWolf", "HiddenWolf", "WhiteWolf", "WolfBeauty"],
    "witch": ["Witch"],
    "post_witch": ["Seer", "GraveyardKeeper", "Raven"],
    "resolution": [],
}

_NIGHT_ORDER = {
    "Cupid": 1,
    "NightmareWolf": 2,
    "Guard": 3,
    "Witch": 4,
    "Seer": 5,
    "GraveyardKeeper": 6,
    "Raven": 7,
    "Werewolf": 8,
}


def _build_mode_options() -> list[GameModeOption]:
    options: list[GameModeOption] = []
    for mode in list_modes():
        player_count: int | None = None
        try:
            cfg = load_config(mode.config_path)
            player_count = len(cfg.players)
        except (ValueError, OSError):
            pass
        options.append(
            GameModeOption(
                participation=mode.participation,
                rules=mode.rules,
                config_path=str(mode.config_path.as_posix()),
                config_id=mode.config_path.stem,
                description=mode.description,
                player_count=player_count,
            )
        )
    return options


def build_home_page(runs_dir: Path, eval_runs_dir: Path, configs_dir: Path) -> HomePageData:
    title, subtitle = get_home_content()
    all_runs = list_run_dirs(runs_dir, eval_runs_dir)
    configs = list_config_files(configs_dir)
    catalog = get_catalog()

    return HomePageData(
        hero=HeroBlock(title=title, subtitle=subtitle),
        nav_links=default_nav_links(),
        stats_cards=[
            StatCard(label="历史对局", value=len(all_runs), unit="局"),
            StatCard(label="角色数量", value=len(catalog), unit="个"),
            StatCard(label="可用配置", value=len(configs), unit="套"),
            StatCard(
                label="含复盘",
                value=sum(1 for r in all_runs if r.has_replay),
                unit="局",
            ),
        ],
        recent_runs=all_runs[:8],
        quick_actions=[
            default_nav_links()[1],
            default_nav_links()[8],
            default_nav_links()[7],
        ],
        game_modes=_build_mode_options(),
    )


def build_about_page(configs_dir: Path) -> AboutPageData:
    base = get_about_page()
    catalog = get_catalog()
    configs = list_config_files(configs_dir)
    return AboutPageData(
        **base.model_dump(),
        tech_stack=["AgentScope", "FastAPI", "Pydantic", "GameEngine", "PostGame Pipeline"],
        architecture_layers=[
            base.sections[0],
            base.sections[1] if len(base.sections) > 1 else base.sections[0],
        ],
        platform_stats={
            "role_count": len(catalog),
            "config_count": len(configs),
            "supported_players": "6-20",
            "camps": len(CAMP_LABELS),
        },
    )


def build_features_page() -> FeaturesPageData:
    base = get_features_page()
    return FeaturesPageData(
        **base.model_dump(),
        feature_cards=[
            FeatureCard(
                key="game_engine",
                title="规则引擎",
                description="完整狼人杀阶段流转与信息隔离",
                icon="engine",
                bullets=["6–20 人板子", "警长流程", "22 种角色"],
            ),
            FeatureCard(
                key="multi_agent",
                title="多 Agent 对局",
                description="每位玩家独立 LLM 决策",
                icon="agents",
                bullets=["结构化输出", "ReAct 推理", "Skill 沉淀"],
            ),
            FeatureCard(
                key="post_game",
                title="赛后分析",
                description="自动复盘与评分",
                icon="chart",
                bullets=["MVP 评分", "投票摇摆", "阵营说服"],
            ),
            FeatureCard(
                key="eval",
                title="批量评测",
                description="Leaderboard 与 A/B 对比",
                icon="leaderboard",
                bullets=["eval_runs", "checkers", "metrics.csv"],
            ),
        ],
    )


def build_how_to_play_page() -> HowToPlayPageData:
    base = get_how_to_play_page()
    return HowToPlayPageData(
        **base.model_dump(),
        phase_flow=[
            PhaseFlowStep(order=1, phase_key="night", title="夜晚", description="各角色按顺序私密行动", icon="moon"),
            PhaseFlowStep(order=2, phase_key="day_discussion", title="白天讨论", description="存活玩家依次发言", icon="sun"),
            PhaseFlowStep(order=3, phase_key="day_voting", title="白天投票", description="投票放逐，平票 PK", icon="vote"),
            PhaseFlowStep(order=4, phase_key="sheriff", title="警长竞选", description="首夜后可选警长流程", icon="badge"),
        ],
        victory_conditions=[
            base.sections[0],
        ],
    )


def build_night_phase_page_enriched() -> NightPhasePageData:
    base = get_night_phase_page()
    preset_12 = next((p for p in build_board_presets() if p.player_count == 12), None)
    timeouts = preset_12.timeouts if preset_12 else {"night": 60, "day": 300, "vote": 60}
    base_dump = base.model_dump(exclude={"involved_roles", "visibility_rules", "timeout_hints"})
    return NightPhasePageData(
        **base_dump,
        involved_roles=_NIGHT_STEP_ROLES,
        visibility_rules=[
            base.sections[0],
            base.sections[0].model_copy(
                update={
                    "heading": "私密事件",
                    "body": "查验、用药、刀口等默认仅行动者（或指定阵营）可见。",
                    "bullets": ["预言家查验 → 仅预言家", "女巫刀口 → 仅女巫", "狼队讨论 → 仅狼人"],
                }
            ),
        ],
        timeout_hints=timeouts,
    )


def build_strategy_page_enriched() -> StrategyPageData:
    base = get_strategy_page()
    phase_tips = [
        StrategyTip(role_key=None, title="首夜信息稀缺", content="神职避免过早暴露；狼人统一刀口。", tags=["夜晚"]),
        StrategyTip(role_key=None, title="白天找矛盾", content="对比前后发言与投票意向变化。", tags=["白天"]),
        StrategyTip(role_key=None, title="末轮票型", content="关注警长 1.5 票与 PK 规则。", tags=["投票"]),
    ]
    by_camp: dict[str, list[StrategyTip]] = {}
    for tip in base.role_tips:
        camp = tip.tags[0] if tip.tags else "other"
        by_camp.setdefault(camp, []).append(tip)
    return StrategyPageData(
        title=base.title,
        general_tips=base.general_tips,
        phase_tips=phase_tips,
        role_tips=base.role_tips,
        role_tips_by_camp=by_camp,
        post_game_links=base.post_game_links,
    )


def build_roles_list_page() -> RoleListPageData:
    base = list_roles_page()
    camps = base.camps
    camp_stats = {camp: len(items) for camp, items in camps.items()}
    return RoleListPageData(
        title=base.title,
        camps=camps,
        camp_stats=camp_stats,
        board_presets=build_board_presets(),
        total=base.total,
    )


def build_role_detail_page(role_key: str) -> RoleDetailPageData:
    detail = get_role_detail(role_key)
    defn = get_definition(role_key)
    related: list[str] = []
    for other in get_catalog():
        if other.name != role_key and other.camp == defn.camp:
            related.append(other.name)
        if len(related) >= 4:
            break
    return RoleDetailPageData(
        **detail.model_dump(),
        board_sizes=board_sizes_for_role(role_key),
        related_roles=related,
        night_action_order=_NIGHT_ORDER.get(role_key),
    )


def build_models_list_page(runs_dir: Path, eval_runs_dir: Path, configs_dir: Path) -> ModelListPageData:
    base = list_models_page(configs_dir)
    base.usage_stats = aggregate_model_usage(runs_dir, eval_runs_dir)
    by_provider: dict[str, list] = {}
    for cfg in base.configs:
        provider = cfg.provider or "unknown"
        by_provider.setdefault(provider, []).append(cfg)
    recommended = [c.config_id for c in base.configs if "demo" not in c.config_id][:3]
    return ModelListPageData(
        title=base.title,
        configs=base.configs,
        by_provider=by_provider,
        usage_stats=base.usage_stats,
        recommended_config_ids=recommended,
    )


def build_model_detail_page(
    model_id: str, runs_dir: Path, eval_runs_dir: Path, configs_dir: Path
) -> ModelDetailPageData:
    base = get_model_detail(model_id, configs_dir)
    usage_map = {u.model_id: u for u in aggregate_model_usage(runs_dir, eval_runs_dir)}
    base.usage = usage_map.get(model_id, base.usage)

    slots: list[ModelPlayerSlot] = []
    if base.configs:
        try:
            cfg_path = Path(base.configs[0].config_path)
            raw = load_config(cfg_path)
            for idx, player in enumerate(raw.players, start=1):
                slots.append(
                    ModelPlayerSlot(
                        seat=idx,
                        name=player.name,
                        model=player.model or player.model_env or "unknown",
                        plan=player.plan,
                        reasoning_effort=str(player.reasoning_effort)
                        if player.reasoning_effort
                        else None,
                    )
                )
        except (ValueError, OSError):
            pass

    return ModelDetailPageData(
        **base.model_dump(exclude={"player_slots"}),
        player_slots=slots,
    )


def build_game_page(
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    run_id: str | None = None,
    source: str | None = None,
    config_id: str | None = None,
) -> GamePageData | None:
    active_run = None
    snapshot = None
    players = []
    camp_counts: dict[str, int] = {}
    recent: list = []
    board_preset: BoardPreset | None = None

    if run_id:
        active_run = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source)
        if active_run is None:
            return None
        run_dir = Path(active_run.path)
        snapshot = extract_game_snapshot(run_dir)
        players = active_run.roster
        camp_counts = extract_camp_counts(run_dir)
        recent = recent_events(run_dir)
        if active_run.player_count:
            matches = [p for p in build_board_presets() if p.player_count == active_run.player_count]
            board_preset = matches[0] if matches else None

    if config_id and board_preset is None:
        for path in list_config_files(Path("configs")):
            if path.stem == config_id:
                brief = parse_config_brief(path)
                if brief:
                    matches = [
                        p for p in build_board_presets() if p.player_count == brief.player_count
                    ]
                    board_preset = matches[0] if matches else None
                break

    return GamePageData(
        title="主游戏",
        modes=_build_mode_options(),
        active_run=active_run,
        snapshot=snapshot,
        board_preset=board_preset,
        players=players,
        camp_counts=camp_counts,
        recent_events=recent,
    )


def build_replay_page_enriched(
    run_id: str,
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    source: str | None = None,
    view: str = "public",
    viewer_id: str | None = None,
) -> ReplayPageData | None:
    base = get_replay_page(
        run_id,
        runs_dir,
        eval_runs_dir,
        source=source,
        view=view,
        viewer_id=viewer_id,
    )
    if base is None:
        return None
    run_dir = Path(base.run.path)
    coach_excerpt = None
    coach_path = run_dir / "coach_summary.json"
    if coach_path.is_file():
        data = _load_json(coach_path)
        if isinstance(data, dict):
            coach_excerpt = str(data.get("summary") or data.get("headline") or "")[:500] or None

    return ReplayPageData(
        run=base.run,
        view_scope=base.view_scope,
        timeline=base.timeline,
        phase_summary=build_phase_summary(run_dir),
        turning_points=build_turning_point_lines(run_dir),
        mvp_ranking=build_mvp_ranking(run_dir),
        scores=base.scores,
        views_available=base.views_available,
        report_markdown=base.report_markdown,
        coach_excerpt=coach_excerpt,
        belief_snapshots=base.belief_snapshots,
        wolf_camp_snapshots=base.wolf_camp_snapshots,
        belief_heatmap=base.belief_heatmap,
    )


def build_share_replay_page_enriched(
    run_id: str, runs_dir: Path, eval_runs_dir: Path, *, source: str | None = None
) -> ShareReplayPageData | None:
    base = get_share_replay_page(run_id, runs_dir, eval_runs_dir, source=source)
    if base is None:
        return None
    detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source)
    if detail is None:
        return None
    run_dir = Path(detail.path)
    mvp = build_mvp_ranking(run_dir)
    mvp_winner = mvp[0] if mvp else None
    moments = build_turning_point_lines(run_dir)[:3]
    winner = base.winner_camp or "未知"
    stats_line = f"{len(base.highlight_players)} 人 · 胜方 {winner}"
    if mvp_winner:
        stats_line += f" · MVP {mvp_winner.player_name}"

    return ShareReplayPageData(
        run_id=base.run_id,
        share_title=base.share_title,
        share_summary=base.share_summary,
        og_title=f"AI 狼人杀 · {winner} 阵营获胜",
        og_description=base.share_summary,
        winner_camp=base.winner_camp,
        mvp_winner=mvp_winner,
        key_moments=moments,
        highlight_players=base.highlight_players,
        share_url_path=base.share_url_path,
        artifacts=base.artifacts,
        stats_line=stats_line,
    )
