"""Adapter layer: AgentScope integration and backward-compatible prompt exports."""

from llm_werewolf.adapter.agent import AgentScopeWerewolfAgent
from llm_werewolf.adapter.bridge import WerewolfAdapterBridge
from llm_werewolf.adapter.factory import configure_agents_for_players, create_react_agent
from llm_werewolf.adapter.information_hub import InformationHub
from llm_werewolf.adapter.message import MessageAdapter, Msg
from llm_werewolf.adapter.prompts import GamePrompts, PlanStrategies, ROLE_SEAT_ACTION, RolePrompts
from llm_werewolf.adapter.setup import bind_agentscope_roles
from llm_werewolf.adapter.visibility import RoutedMessage, VisibilityChannel
from llm_werewolf.core.prompts import PromptManager, SYSTEM_PROMPT

__all__ = [
    "AgentScopeWerewolfAgent",
    "GamePrompts",
    "InformationHub",
    "MessageAdapter",
    "Msg",
    "PlanStrategies",
    "PromptManager",
    "ROLE_SEAT_ACTION",
    "RolePrompts",
    "RoutedMessage",
    "SYSTEM_PROMPT",
    "VisibilityChannel",
    "WerewolfAdapterBridge",
    "bind_agentscope_roles",
    "configure_agents_for_players",
    "create_react_agent",
]
