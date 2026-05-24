"""Compatibility exports for AgentScope agent factory helpers."""

from llm_werewolf.agent_team.factory import (
    GAME_ROLE_TO_PROMPT_KEY,
    PROMPT_KEY_TO_ROLE_CONFIG,
    build_system_prompt,
    configure_agents_for_players,
    create_react_agent,
    player_id_to_seat,
    resolve_plan_text,
)

__all__ = [
    "GAME_ROLE_TO_PROMPT_KEY",
    "PROMPT_KEY_TO_ROLE_CONFIG",
    "build_system_prompt",
    "configure_agents_for_players",
    "create_react_agent",
    "player_id_to_seat",
    "resolve_plan_text",
]
