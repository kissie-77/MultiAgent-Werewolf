"""根据玩家配置构建 AgentScope ReAct Agent 的工厂。"""

from __future__ import annotations

import os

from llm_werewolf.game_runtime.env import load_project_dotenv

load_project_dotenv()
from typing import TYPE_CHECKING, Any

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

from llm_werewolf.agent_team.memory import MemoryManager
from llm_werewolf.game_runtime.config import MemoryConfig, PlayerConfig
from llm_werewolf.game_runtime.prompts.manager import PromptManager

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.player import Player

GAME_ROLE_TO_PROMPT_KEY = PromptManager.GAME_ROLE_TO_PROMPT_KEY
PROMPT_KEY_TO_ROLE_CONFIG = PromptManager.get_role_strategy_configs()


def player_id_to_seat(player_id: str) -> int:
    """将 player_id（如 'player_3'）转换为座位号 3。"""
    return int(player_id.rsplit("_", 1)[-1])


def resolve_plan_text(plan_name: str, prompt_role_key: str) -> str:
    """将策略计划名称解析为对应角色的 prompt 文本。"""
    return PromptManager.resolve_plan_text(plan_name, prompt_role_key)


def build_system_prompt(
    seat_number: int,
    game_role_name: str,
    plan_text: str,
    *,
    prompt_version: str = "v2",
    include_role_skills: bool = True,
) -> str:
    """为已知角色的就座玩家构建系统 prompt。"""
    base = PromptManager.build_role_strategy_prompt(
        seat_number,
        game_role_name,
        plan_text,
        prompt_version=prompt_version,
    )
    if not include_role_skills:
        return base
    prompt_key = PromptManager.get_prompt_role_key(game_role_name)
    from llm_werewolf.agent_team.skill_loader import load_role_skills_text

    skills = load_role_skills_text(prompt_key)
    if skills:
        return f"{base}\n\n{skills}"
    return base


def create_react_agent(
    config: PlayerConfig,
    *,
    agent_name: str,
    sys_prompt: str,
) -> ReActAgent:
    """创建接入 OpenAI 兼容端点的 AgentScope ReActAgent。"""
    api_key = None
    if config.api_key_env:
        api_key = os.getenv(config.api_key_env)
    if not api_key:
        msg = (
            f"API key not found in environment variable "
            f"'{config.api_key_env}' for player '{config.name}'"
        )
        raise ValueError(msg)

    if not config.base_url:
        msg = f"base_url is required for AgentScope player '{config.name}'"
        raise ValueError(msg)

    generate_kwargs: dict[str, Any] = {"max_tokens": 2048}
    if config.reasoning_effort:
        generate_kwargs["reasoning_effort"] = config.reasoning_effort

    model = OpenAIChatModel(
        model_name=config.model,
        api_key=api_key,
        client_kwargs={"base_url": config.base_url},
        stream=False,
        generate_kwargs=generate_kwargs,
    )

    return ReActAgent(
        name=agent_name,
        sys_prompt=sys_prompt,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=Toolkit(),
        memory=InMemoryMemory(),
        print_hint_msg=False,
    )


def _build_compressor(config: MemoryConfig, player_config: PlayerConfig | None = None):
    """为工作记忆构建 LLM 压缩器，配置不足时返回 None。"""
    if not config.enable_llm_working_compression:
        return None

    api_key = config.working_compression_api_key
    base_url = config.working_compression_base_url
    if not api_key and player_config and player_config.api_key_env:
        api_key = os.getenv(player_config.api_key_env, "")
    if not base_url and player_config and player_config.base_url:
        base_url = player_config.base_url
    if not api_key or not base_url:
        return None

    from llm_werewolf.agent_team.memory.llm_compressor import LLMCompressor

    return LLMCompressor(
        api_key=api_key,
        base_url=base_url,
        model=config.working_compression_model,
        timeout=config.working_compression_timeout,
    )


def _build_memory_manager(
    player: Player,
    role_name: str,
    plan_name: str,
    memory_config: MemoryConfig | None,
    event_logger=None,
) -> MemoryManager | None:
    """按玩家当前运行时上下文构建记忆管理器。"""
    if event_logger is None:
        return None

    config = memory_config or MemoryConfig()
    player_config = getattr(player.agent, "player_config", None)
    compressor = _build_compressor(config, player_config)

    manager = MemoryManager(
        event_logger=event_logger,
        role=PromptManager.get_prompt_role_key(role_name),
        player_id=player.player_id,
        plan_name=plan_name,
        config=config,
        compressor=compressor,
    )
    manager.on_game_start(manager.role)
    return manager


def configure_agents_for_players(
    players: list[Player],
    *,
    default_plan: str = "default",
    memory_config: MemoryConfig | None = None,
    prompt_version: str = "v2",
    event_logger=None,
) -> None:
    """角色分配后，为每个 AgentScope Agent 配置系统 prompt。"""
    for player in players:
        agent = player.agent
        seat = player_id_to_seat(player.player_id)
        role_name = player.get_role_name()
        plan_name = getattr(agent, "plan_name", None) or default_plan
        prompt_key = PromptManager.get_prompt_role_key(role_name)
        plan_text = resolve_plan_text(plan_name, prompt_key)

        bind_prompt = getattr(agent, "bind_role_prompt", None)
        if callable(bind_prompt):
            bind_prompt(role_name, seat, plan_text, prompt_version=prompt_version)
            if hasattr(agent, "memory_manager"):
                agent.memory_manager = _build_memory_manager(
                    player,
                    role_name,
                    plan_name,
                    memory_config,
                    event_logger=event_logger,
                )
            continue

        configure_role = getattr(agent, "configure_role", None)
        if not callable(configure_role):
            continue

        configure_role(
            seat_number=seat,
            game_role_name=role_name,
            plan_text=plan_text,
            prompt_version=prompt_version,
        )
        if hasattr(agent, "memory_manager"):
            agent.memory_manager = _build_memory_manager(
                player,
                role_name,
                plan_name,
                memory_config,
                event_logger=event_logger,
            )
