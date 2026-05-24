"""Adapter compatibility package.

The architecture migration keeps this package importable, but exported symbols
are loaded lazily to avoid circular imports between ``agent_team`` and
``adapter``.
"""

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
    "create_players_from_config",
    "prepare_game_roster",
    "wire_agentscope_after_setup",
]


def __getattr__(name: str):
    if name == "AgentScopeWerewolfAgent":
        from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent

        return AgentScopeWerewolfAgent
    if name == "WerewolfAdapterBridge":
        from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge

        return WerewolfAdapterBridge
    if name in {"configure_agents_for_players", "create_react_agent"}:
        from llm_werewolf.agent_team import factory

        return getattr(factory, name)
    if name == "InformationHub":
        from llm_werewolf.agent_team.information_hub import InformationHub

        return InformationHub
    if name in {"RoutedMessage", "VisibilityChannel"}:
        from llm_werewolf.agent_team import visibility

        return getattr(visibility, name)
    if name in {"GamePrompts", "PlanStrategies", "ROLE_SEAT_ACTION", "RolePrompts"}:
        from llm_werewolf.strategy import role_prompts

        return getattr(role_prompts, name)
    if name in {"MessageAdapter", "Msg"}:
        from llm_werewolf.adapter import message

        return getattr(message, name)
    if name in {
        "bind_agentscope_roles",
        "create_players_from_config",
        "prepare_game_roster",
        "wire_agentscope_after_setup",
    }:
        from llm_werewolf.adapter import bootstrap

        return getattr(bootstrap, name)
    if name in {"PromptManager", "SYSTEM_PROMPT"}:
        from llm_werewolf.core import prompts

        return getattr(prompts, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
