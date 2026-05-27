"""根据玩家配置构建 AgentScope ReAct Agent 的工厂。"""

from __future__ import annotations

import os
from types import MethodType

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
    setattr(memory, "_llm_werewolf_strip_thinking_wrapped", True)
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
        "post_reasoning",
        "complete_structured_generate_response_reply",
        _post_reasoning,
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

    agent = ReActAgent(
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
    if not api_key and player_config and player_config.api_key_env:
        api_key = os.getenv(player_config.api_key_env, "")
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
