"""Adapter layer for AgentScope integration."""

from llm_werewolf.adapter.message import MessageAdapter, Msg
from llm_werewolf.adapter.agent import AgentScopeWerewolfAgent
from llm_werewolf.adapter.prompts import RolePrompts, PlanStrategies, GamePrompts

__all__ = [
    "MessageAdapter",
    "Msg",
    "AgentScopeWerewolfAgent",
    "RolePrompts",
    "PlanStrategies",
    "GamePrompts",
]
