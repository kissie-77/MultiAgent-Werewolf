"""创建玩家并在角色分配后接入 AgentScope 的统一入口。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.adapter.factory import configure_agents_for_players
from llm_werewolf.core.agent import create_agent
from llm_werewolf.core.config import PlayersConfig, create_game_config_from_player_count
from llm_werewolf.core.role_registry import create_roles

if TYPE_CHECKING:
    from llm_werewolf.core import GameEngine
    from llm_werewolf.core.agent import DemoAgent, HumanAgent, LLMAgent
    from llm_werewolf.core.config import GameConfig
    from llm_werewolf.core.game_state import GameState
    from llm_werewolf.core.types import AgentProtocol, RoleProtocol

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
) -> None:
    """角色分配完成后，为各玩家配置 AgentScope 系统 prompt。"""
    if game_state is None:
        return
    configure_agents_for_players(game_state.players, default_plan=default_plan)


def create_players_from_config(
    players_config: PlayersConfig,
) -> list[DemoAgent | HumanAgent | LLMAgent]:
    """从 YAML 构建座位 Agent（当 ``agent_backend`` 指定时使用 AgentScope）。"""
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


def wire_agentscope_after_setup(
    engine: GameEngine,
    players_config: PlayersConfig,
) -> None:
    """在 ``GameEngine.setup_game`` 之后绑定 RolePrompts 并创建 ReAct Agent。"""
    if not players_config.use_agentscope_backend:
        return
    bind_agentscope_roles(engine.game_state, default_plan=players_config.default_plan)


def prepare_game_roster(
    players_config: PlayersConfig,
) -> tuple[list[AgentProtocol], list[RoleProtocol], GameConfig]:
    """单局对局的玩家列表、洗牌后的角色实例与板子配置。"""
    game_config = create_game_config_from_player_count(len(players_config.players))
    players = create_players_from_config(players_config)
    roles = create_roles(role_names=game_config.role_names)
    return players, roles, game_config
