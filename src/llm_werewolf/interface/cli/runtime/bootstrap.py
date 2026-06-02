"""创建玩家并在角色分配后接入 AgentScope 的统一入口。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.config import PlayersConfig, create_game_config_from_player_count
from llm_werewolf.agent_team.agents.base import create_agent
from llm_werewolf.agent_team.agents.factory import configure_agents_for_players
from llm_werewolf.game_runtime.registries.role_registry import create_roles
from llm_werewolf.agent_team.communication.information_hub import InformationHub
from llm_werewolf.strategy.role_version_manifest import RoleVersionManifest, set_active_manifest

if TYPE_CHECKING:
    from llm_werewolf.game_runtime import GameEngine
    from llm_werewolf.game_runtime.types import RoleProtocol, AgentProtocol
    from llm_werewolf.game_runtime.config import GameConfig
    from llm_werewolf.agent_team.agents.base import BaseAgent
    from llm_werewolf.game_runtime.state.game_state import GameState

__all__ = [
    "bind_agentscope_roles",
    "create_information_hub",
    "create_players_from_config",
    "prepare_game_roster",
    "wire_agentscope_after_setup",
]


def create_information_hub() -> InformationHub:
    """创建运行时 Agent 通信 Hub。"""
    return InformationHub()


def bind_agentscope_roles(
    game_state: GameState | None,
    *,
    default_plan: str = "default",
    memory_config=None,
    role_version_manifest: RoleVersionManifest | None = None,
) -> None:
    """角色分配完成后，为各玩家配置 AgentScope 系统 prompt。"""
    if game_state is None:
        return
    if role_version_manifest is not None:
        set_active_manifest(role_version_manifest)
    event_logger = getattr(game_state, "event_logger", None)
    configure_agents_for_players(
        game_state.players,
        default_plan=default_plan,
        memory_config=memory_config,
        event_logger=event_logger,
    )


def create_players_from_config(players_config: PlayersConfig) -> list[BaseAgent]:
    """从 YAML 构建座位 Agent（当 ``agent_backend`` 指定时使用 AgentScope）。"""
    set_active_manifest(players_config.role_version_manifest())
    use_agentscope = players_config.use_agentscope_backend
    return [
        create_agent(
            player_cfg,
            language=players_config.language,
            use_agentscope=use_agentscope,
            default_plan=players_config.default_plan,
        )
        for player_cfg in players_config.players
    ]


def wire_agentscope_after_setup(engine: GameEngine, players_config: PlayersConfig) -> None:
    """在 ``GameEngine.setup_game`` 之后绑定策略 Prompt 并创建 ReAct Agent。"""
    if not players_config.use_agentscope_backend:
        return
    bind_agentscope_roles(
        engine.game_state,
        default_plan=players_config.default_plan,
        memory_config=players_config.memory,
        role_version_manifest=players_config.role_version_manifest(),
    )


def prepare_game_roster(
    players_config: PlayersConfig,
) -> tuple[list[AgentProtocol], list[RoleProtocol], GameConfig]:
    """单局对局的玩家列表、洗牌后的角色实例与板子配置。"""
    game_config = create_game_config_from_player_count(len(players_config.players))
    updates: dict[str, int] = {
        "vote_intention_concurrency": players_config.vote_intention_concurrency,
    }
    if players_config.day_timeout is not None:
        updates["day_timeout"] = players_config.day_timeout
    if players_config.vote_timeout is not None:
        updates["vote_timeout"] = players_config.vote_timeout
    if players_config.night_timeout is not None:
        updates["night_timeout"] = players_config.night_timeout
    game_config = game_config.model_copy(update=updates)
    players = create_players_from_config(players_config)
    roles = create_roles(role_names=game_config.role_names)
    return players, roles, game_config
