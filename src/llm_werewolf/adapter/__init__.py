"""Adapter layer for AgentScope integration."""

from llm_werewolf.adapter.message import MessageAdapter, Msg
from llm_werewolf.adapter.agent import AgentScopeWerewolfAgent
from llm_werewolf.adapter.bridge import WerewolfAdapterBridge
from llm_werewolf.adapter.factory import configure_agents_for_players, create_react_agent
from llm_werewolf.adapter.information_hub import InformationHub
from llm_werewolf.adapter.prompts import RolePrompts, PlanStrategies, GamePrompts, ROLE_SEAT_ACTION
from llm_werewolf.adapter.setup import bind_agentscope_roles
from llm_werewolf.adapter.visibility import RoutedMessage, VisibilityChannel

__all__ = [
    "MessageAdapter",
    "Msg",
    "AgentScopeWerewolfAgent",
    "WerewolfAdapterBridge",
    "InformationHub",
    "RoutedMessage",
    "VisibilityChannel",
    "RolePrompts",
    "PlanStrategies",
    "GamePrompts",
    "create_react_agent",
    "configure_agents_for_players",
    "bind_agentscope_roles",
]
