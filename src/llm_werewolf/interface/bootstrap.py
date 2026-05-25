"""创建玩家并在角色分配后接入 AgentScope 的统一入口。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.agent_team.base import create_agent
from llm_werewolf.agent_team.factory import configure_agents_for_players
from llm_werewolf.game_runtime.config import (
    PlayerConfig,
    PlayersConfig,
    create_game_config_from_player_count,
)
from llm_werewolf.interface.player_roster import resolve_player_configs
from llm_werewolf.game_runtime.role_registry import create_roles

if TYPE_CHECKING:
    from llm_werewolf.game_runtime import GameEngine
    from llm_werewolf.agent_team.base import BaseAgent
    from llm_werewolf.game_runtime.types import RoleProtocol, AgentProtocol
    from llm_werewolf.game_runtime.config import GameConfig
    from llm_werewolf.game_runtime.game_state import GameState

__all__ = [
    "bind_agentscope_roles",
    "create_players_from_config",
    "prepare_game_roster",
    "wire_agentscope_after_setup",
]


def bind_agentscope_roles(
    game_state: GameState | None,
    *,
    default_plan: str = "default",
    show_agent_raw: bool = False,
) -> None:
    """角色分配完成后，为各玩家配置 AgentScope 系统 prompt。"""
    if game_state is None:
        return
    configure_agents_for_players(
        game_state.players,
        default_plan=default_plan,
        show_agent_raw=show_agent_raw,
    )


def create_players_from_config(
    players_config: PlayersConfig,
    *,
    num_players: int | None = None,
) -> list[BaseAgent]:
    """从 YAML 构建座位 Agent（当 ``agent_backend`` 指定时使用 AgentScope）。"""
    player_configs = resolve_player_configs(players_config, num_players=num_players)
    return _create_players_from_player_configs(players_config, player_configs)


def _create_players_from_player_configs(
    players_config: PlayersConfig,
    player_configs: list[PlayerConfig],
) -> list[BaseAgent]:
    use_agentscope = players_config.use_agentscope_backend
    return [
        create_agent(
            player_cfg,
            language=players_config.language,
            use_agentscope=use_agentscope,
            default_plan=players_config.default_plan,
        )
        for player_cfg in player_configs
    ]


def wire_agentscope_after_setup(
    engine: GameEngine,
    players_config: PlayersConfig,
    *,
    show_agent_raw: bool = False,
) -> None:
    """在 ``GameEngine.setup_game`` 之后绑定策略 Prompt 并创建 ReAct Agent。"""
    if not players_config.use_agentscope_backend:
        return
    bind_agentscope_roles(
        engine.game_state,
        default_plan=players_config.default_plan,
        show_agent_raw=show_agent_raw,
    )


def prepare_game_roster(
    players_config: PlayersConfig,
    *,
    num_players: int | None = None,
    enable_sheriff: bool | None = None,
) -> tuple[list[AgentProtocol], list[RoleProtocol], GameConfig]:
    """单局对局的玩家列表、洗牌后的角色实例与板子配置。"""
    player_configs = resolve_player_configs(players_config, num_players=num_players)
    game_config = create_game_config_from_player_count(len(player_configs))
    if enable_sheriff is not None:
        game_config.enable_sheriff = enable_sheriff
    players = _create_players_from_player_configs(players_config, player_configs)
    roles = create_roles(role_names=game_config.role_names)
    return players, roles, game_config
