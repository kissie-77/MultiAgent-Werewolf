"""Factory for building AgentScope ReAct agents from player configuration."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

from llm_werewolf.adapter.prompts import PlanStrategies, RolePrompts
from llm_werewolf.core.config import PlayerConfig

if TYPE_CHECKING:
    from llm_werewolf.core.player import Player

# Map game engine role names to RolePrompts keys in adapter/prompts.py
GAME_ROLE_TO_PROMPT_KEY: dict[str, str] = {
    "Villager": "villager",
    "Seer": "prophet",
    "Witch": "witch",
    "Hunter": "hunter",
    "Guard": "guard",
    "Werewolf": "wolf",
    "AlphaWolf": "wolf_king",
    "WhiteWolf": "wolf",
    "WolfBeauty": "wolf",
    "GuardianWolf": "wolf",
    "HiddenWolf": "wolf",
    "NightmareWolf": "wolf",
    "BloodMoonApostle": "wolf",
    "Idiot": "villager",
    "Elder": "villager",
    "Knight": "villager",
    "Cupid": "villager",
    "Raven": "villager",
    "Magician": "villager",
    "GraveyardKeeper": "villager",
    "Thief": "villager",
    "Lover": "villager",
}

PROMPT_KEY_TO_ROLE_CONFIG: dict[str, dict[str, str]] = {
    "villager": RolePrompts.VILLAGER,
    "prophet": RolePrompts.PROPHET,
    "witch": RolePrompts.WITCH,
    "wolf": RolePrompts.WOLF,
    "wolf_king": RolePrompts.WOLF_KING,
    "guard": RolePrompts.GUARD,
    "hunter": RolePrompts.HUNTER,
}


def player_id_to_seat(player_id: str) -> int:
    """Convert player_id like 'player_3' to seat number 3."""
    return int(player_id.rsplit("_", 1)[-1])


def resolve_plan_text(plan_name: str, prompt_role_key: str) -> str:
    """Resolve plan strategy name to prompt text for a role."""
    plan = PlanStrategies.get_plan_by_name(plan_name)
    return plan.get(prompt_role_key, plan.get("villager", "自由发挥"))


def build_system_prompt(
    seat_number: int,
    game_role_name: str,
    plan_text: str,
) -> str:
    """Build RolePrompts.BASE_PROMPT for a seated player with known role."""
    prompt_role_key = GAME_ROLE_TO_PROMPT_KEY.get(game_role_name, "villager")
    role_config = PROMPT_KEY_TO_ROLE_CONFIG.get(prompt_role_key, RolePrompts.VILLAGER)

    return RolePrompts.BASE_PROMPT.format(
        number=seat_number,
        role_name=role_config["role_name"],
        role_instruction=role_config["role_instruction"],
        suggestion=role_config["suggestion"],
        plan=plan_text,
    )


def create_react_agent(
    config: PlayerConfig,
    *,
    agent_name: str,
    sys_prompt: str,
) -> ReActAgent:
    """Create an AgentScope ReActAgent wired to an OpenAI-compatible endpoint."""
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


def configure_agents_for_players(
    players: list[Player],
    *,
    default_plan: str = "default",
) -> None:
    """After roles are assigned, configure each AgentScope agent's system prompt."""
    from llm_werewolf.adapter.agent import AgentScopeWerewolfAgent

    for player in players:
        agent = player.agent
        if not isinstance(agent, AgentScopeWerewolfAgent):
            continue

        seat = player_id_to_seat(player.player_id)
        role_name = player.get_role_name()
        plan_name = agent.plan_name or default_plan
        plan_text = resolve_plan_text(plan_name, GAME_ROLE_TO_PROMPT_KEY.get(role_name, "villager"))

        agent.configure_role(
            seat_number=seat,
            game_role_name=role_name,
            plan_text=plan_text,
        )
