"""根据玩家配置构建 AgentScope ReAct Agent 的工厂。"""

from __future__ import annotations

import os
from types import MethodType
from random import Random
from collections import Counter

from llm_werewolf.game_runtime.support.env import load_project_dotenv

load_project_dotenv()
from typing import TYPE_CHECKING, Any

from agentscope.tool import Toolkit
from agentscope.model import OpenAIChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import OpenAIChatFormatter

from llm_werewolf.agent_team.memory import RuntimeMemoryManager
from llm_werewolf.game_runtime.config import MemoryConfig, PlayerConfig, PlanAssignmentConfig
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.agent_team.agents.fast_react_agent import FastReActAgent

if TYPE_CHECKING:
    from agentscope.agent import ReActAgent

    from llm_werewolf.game_runtime.state.player import Player

GAME_ROLE_TO_PROMPT_KEY = PromptManager.GAME_ROLE_TO_PROMPT_KEY
PROMPT_KEY_TO_ROLE_CONFIG = PromptManager.get_role_strategy_configs()


def _strip_thinking_from_content(content: Any) -> Any:
    """Remove AgentScope thinking blocks while preserving other multimodal blocks."""
    if not isinstance(content, list):
        return content
    return [
        block
        for block in content
        if not (isinstance(block, dict) and block.get("type") == "thinking")
    ]


def _strip_thinking_from_msg_payload(payload: Any) -> Any:
    """Sanitize Msg or list[Msg] payloads by removing thinking blocks in-place."""
    if isinstance(payload, list):
        return [_strip_thinking_from_msg_payload(item) for item in payload]
    content = getattr(payload, "content", None)
    sanitized = _strip_thinking_from_content(content)
    if sanitized is not content:
        payload.content = sanitized
    return payload


def _wrap_memory_add_without_thinking(agent: ReActAgent) -> ReActAgent:
    """Ensure AgentScope memory never stores thinking blocks."""
    memory = getattr(agent, "memory", None)
    if memory is None or not hasattr(memory, "add"):
        return agent
    if getattr(memory, "_llm_werewolf_strip_thinking_wrapped", False):
        return agent

    original_add = memory.add

    async def _sanitized_add(self, msg: Any = None, *args: Any, **kwargs: Any) -> Any:
        sanitized_msg = _strip_thinking_from_msg_payload(msg)
        return await original_add(sanitized_msg, *args, **kwargs)

    memory.add = MethodType(_sanitized_add, memory)
    memory._llm_werewolf_strip_thinking_wrapped = True
    return agent


def _register_no_thinking_print_hook(agent: ReActAgent) -> ReActAgent:
    """Prevent AgentScope console printing from exposing reasoning blocks."""

    def _pre_print(_self, kwargs: dict[str, Any]) -> dict[str, Any]:
        msg = kwargs.get("msg")
        if msg is None:
            return kwargs
        content = getattr(msg, "content", None)
        sanitized = _strip_thinking_from_content(content)
        if sanitized is content:
            return kwargs
        msg.content = sanitized
        kwargs["msg"] = msg
        return kwargs

    agent.register_instance_hook("pre_print", "strip_thinking_blocks", _pre_print)
    return _wrap_memory_add_without_thinking(agent)


def _register_structured_tool_reply_completion_hook(agent: ReActAgent) -> ReActAgent:
    """Avoid an extra free-text turn after a structured generate_response call."""

    def _post_reasoning(self, _kwargs: dict[str, Any], msg: Any) -> Any:
        if getattr(self, "_required_structured_model", None) is None:
            return None
        if msg is None or not hasattr(msg, "get_content_blocks"):
            return None
        finish_name = getattr(self, "finish_function_name", "generate_response")
        tool_blocks = msg.get_content_blocks("tool_use")
        if not any(block.get("name") == finish_name for block in tool_blocks):
            return None
        if msg.get_content_blocks("text"):
            return None
        if not isinstance(getattr(msg, "content", None), list):
            return None
        msg.content.append({"type": "text", "text": "Structured response submitted."})
        return msg

    agent.register_instance_hook(
        "post_reasoning", "complete_structured_generate_response_reply", _post_reasoning
    )
    return agent


def _disable_agentscope_console_output(agent: ReActAgent) -> ReActAgent:
    """Let the game engine own user-facing logs instead of AgentScope internals."""
    if hasattr(agent, "_disable_console_output"):
        agent._disable_console_output = True
    return agent


def player_id_to_seat(player_id: str) -> int:
    """将 player_id（如 'player_3'）转换为座位号 3。"""
    return int(player_id.rsplit("_", 1)[-1])


def resolve_plan_text(plan_name: str, prompt_role_key: str) -> str:
    """将策略计划名称解析为对应角色的 prompt 文本。"""
    return PromptManager.resolve_plan_text(plan_name, prompt_role_key)


def _role_counts(players: list[Player]) -> dict[str, int]:
    counts = Counter(player.get_role_name() for player in players)
    return dict(sorted(counts.items()))


def _manual_plan_name(agent: Any) -> str | None:
    """Return a YAML-specified player plan, if present."""
    player_config = getattr(agent, "player_config", None)
    plan = getattr(player_config, "plan", None)
    if isinstance(plan, str) and plan.strip():
        return plan.strip()
    return None


def _role_plan_names(prompt_role_key: str, plan_assignment: PlanAssignmentConfig) -> list[str]:
    explicit = plan_assignment.role_plans.get(prompt_role_key)
    if explicit:
        return [name for name in explicit if name]

    from llm_werewolf.strategy.registry.role_prompts import PlanStrategies

    return PlanStrategies.default_role_style_plan_names(prompt_role_key)


def assign_role_plan_names(
    players: list[Player],
    *,
    default_plan: str,
    plan_assignment: PlanAssignmentConfig | None = None,
) -> dict[str, str]:
    """Assign plan names after roles are known, preserving manual player plans."""
    assignments: dict[str, str] = {}
    if plan_assignment is None or not plan_assignment.enabled:
        return assignments

    rng = Random(plan_assignment.seed)
    counters: dict[str, int] = {}
    randomized_pools: dict[str, list[str]] = {}

    for player in players:
        agent = player.agent
        if _manual_plan_name(agent):
            continue

        prompt_key = PromptManager.get_prompt_role_key(player.get_role_name())
        plan_names = _role_plan_names(prompt_key, plan_assignment)
        if not plan_names:
            assignments[player.player_id] = default_plan
            continue

        index = counters.get(prompt_key, 0)
        counters[prompt_key] = index + 1

        if plan_assignment.mode == "role_random":
            pool = randomized_pools.get(prompt_key)
            if pool is None:
                pool = list(plan_names)
                rng.shuffle(pool)
                randomized_pools[prompt_key] = pool
            assignments[player.player_id] = pool[index % len(pool)]
        else:
            assignments[player.player_id] = plan_names[index % len(plan_names)]

    return assignments


def build_system_prompt(
    seat_number: int,
    game_role_name: str,
    plan_text: str,
    *,
    include_role_skills: bool = True,
    role_counts: dict[str, int] | None = None,
) -> str:
    """为已知角色的就座玩家构建系统 prompt。"""
    from llm_werewolf.strategy.registry.role_version_manifest import get_active_manifest

    prompt_key = PromptManager.get_prompt_role_key(game_role_name)
    manifest = get_active_manifest()
    base = PromptManager.build_role_strategy_prompt(
        seat_number,
        game_role_name,
        plan_text,
        prompt_version=manifest.prompt_version_for(prompt_key),
    )
    role_pool_text = ""
    if role_counts:
        from llm_werewolf.game_runtime.prompts.actions import EngineContexts

        role_pool_text = EngineContexts.role_pool_note(role_counts)
    if include_role_skills:
        base = (
            f"{base}\n\n"
            "【对局经验 Skill】将根据当前信念矩阵（B1/B2/投票意向）动态注入决策上下文。"
        )
    if role_pool_text:
        base = f"{base}\n\n{role_pool_text}"
    return base


def create_react_agent(
    config: PlayerConfig,
    *,
    agent_name: str,
    sys_prompt: str,
) -> ReActAgent:
    """创建接入 OpenAI 兼容端点的 AgentScope ReActAgent。"""
    api_key = config.api_key or (
        os.getenv(config.api_key_env) if config.api_key_env else None
    )
    if not api_key:
        msg = (
            f"API key not found: set literal api_key or env var "
            f"'{config.api_key_env}' for player '{config.name}'"
        )
        raise ValueError(msg)

    if not config.base_url:
        msg = f"base_url is required for AgentScope player '{config.name}'"
        raise ValueError(msg)

    generate_kwargs: dict[str, Any] = {"max_tokens": 2048}
    if config.reasoning_effort:
        generate_kwargs["reasoning_effort"] = config.reasoning_effort
    if config.temperature is not None:
        generate_kwargs["temperature"] = config.temperature

    model = OpenAIChatModel(
        model_name=config.model,
        api_key=api_key,
        client_kwargs={"base_url": config.base_url},
        stream=False,
        generate_kwargs=generate_kwargs,
    )

    agent = FastReActAgent(
        name=agent_name,
        sys_prompt=sys_prompt,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=Toolkit(),
        memory=InMemoryMemory(),
        print_hint_msg=False,
    )
    agent = _register_no_thinking_print_hook(agent)
    agent = _register_structured_tool_reply_completion_hook(agent)
    return _disable_agentscope_console_output(agent)


def _build_compressor(config: MemoryConfig, player_config: PlayerConfig | None = None):
    """为工作记忆构建 LLM 压缩器，配置不足时返回 None。"""
    if not config.enable_llm_working_compression:
        return None

    api_key = config.working_compression_api_key
    base_url = config.working_compression_base_url
    if not api_key and player_config:
        api_key = player_config.api_key or (
            os.getenv(player_config.api_key_env, "") if player_config.api_key_env else ""
        )
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
    role_counts: dict[str, int] | None = None,
) -> RuntimeMemoryManager | None:
    """按玩家当前运行时上下文构建记忆管理器。"""
    if event_logger is None:
        return None

    config = memory_config or MemoryConfig()
    player_config = getattr(player.agent, "player_config", None)
    compressor = _build_compressor(config, player_config)

    manager = RuntimeMemoryManager(
        event_logger=event_logger,
        role=PromptManager.get_prompt_role_key(role_name),
        player_id=player.player_id,
        plan_name=plan_name,
        config=config,
        compressor=compressor,
    )
    manager.on_game_start(manager.role, role_counts=role_counts)
    return manager


def configure_agents_for_players(
    players: list[Player],
    *,
    default_plan: str = "default",
    plan_assignment: PlanAssignmentConfig | None = None,
    memory_config: MemoryConfig | None = None,
    event_logger=None,
) -> None:
    """角色分配后，为每个 AgentScope Agent 配置系统 prompt。"""
    from llm_werewolf.strategy.registry.role_version_manifest import get_active_manifest

    manifest = get_active_manifest()
    role_counts = _role_counts(players)
    assigned_plan_names = assign_role_plan_names(
        players, default_plan=default_plan, plan_assignment=plan_assignment
    )
    for player in players:
        agent = player.agent
        seat = player_id_to_seat(player.player_id)
        role_name = player.get_role_name()
        plan_name = (
            _manual_plan_name(agent)
            or assigned_plan_names.get(player.player_id)
            or getattr(agent, "plan_name", None)
            or default_plan
        )
        prompt_key = PromptManager.get_prompt_role_key(role_name)
        plan_text = resolve_plan_text(plan_name, prompt_key)
        role_prompt_version = manifest.prompt_version_for(prompt_key)

        bind_prompt = getattr(agent, "bind_role_prompt", None)
        bind_role_fn = getattr(agent, "bind_role", None)
        if callable(bind_role_fn) and not callable(bind_prompt):
            bind_role_fn(type(player.role), seat, plan_name)
            if hasattr(agent, "player_count"):
                agent.player_count = len(players)
            continue

        if callable(bind_prompt):
            bind_prompt(
                role_name,
                seat,
                plan_text,
                prompt_version=role_prompt_version,
                player_count=len(players),
                role_counts=role_counts,
            )
            if hasattr(agent, "memory_manager"):
                agent.memory_manager = _build_memory_manager(
                    player,
                    role_name,
                    plan_name,
                    memory_config,
                    event_logger=event_logger,
                    role_counts=role_counts,
                )
            continue

        configure_role = getattr(agent, "configure_role", None)
        if not callable(configure_role):
            continue

        configure_role(
            seat_number=seat,
            game_role_name=role_name,
            plan_text=plan_text,
            prompt_version=role_prompt_version,
            role_counts=role_counts,
        )
        if hasattr(agent, "memory_manager"):
            agent.memory_manager = _build_memory_manager(
                player,
                role_name,
                plan_name,
                memory_config,
                event_logger=event_logger,
                role_counts=role_counts,
            )
