"""Helpers to wire AgentScope agents into the game engine after setup."""

from llm_werewolf.adapter.factory import configure_agents_for_players
from llm_werewolf.core.game_state import GameState

__all__ = ["bind_agentscope_roles"]


def bind_agentscope_roles(
    game_state: GameState | None,
    *,
    default_plan: str = "default",
) -> None:
    """Configure AgentScope system prompts once roles are assigned to players."""
    if game_state is None:
        return
    configure_agents_for_players(game_state.players, default_plan=default_plan)
