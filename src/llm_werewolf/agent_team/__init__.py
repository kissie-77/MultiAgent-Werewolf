"""Multi-agent runtime integration."""

__all__ = [
    "AgentScopeWerewolfAgent",
    "BaseAgent",
    "DemoAgent",
    "MemoryConfig",
    "MemoryManager",
    "ProceduralMemory",
    "PromptAgentMixin",
    "SemanticMemory",
    "skill_loader",
    "WorkingMemory",
    "configure_agents_for_players",
    "create_agent",
    "create_react_agent",
]


def __getattr__(name: str):
    if name == "AgentScopeWerewolfAgent":
        from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent

        return AgentScopeWerewolfAgent
    if name in {"BaseAgent", "DemoAgent", "create_agent"}:
        from llm_werewolf.agent_team.agents import base

        return getattr(base, name)
    if name in {
        "MemoryConfig",
        "MemoryManager",
        "ProceduralMemory",
        "SemanticMemory",
        "WorkingMemory",
    }:
        from llm_werewolf.agent_team import memory

        return getattr(memory, name)
    if name == "skill_loader":
        from llm_werewolf.agent_team.skill_support import skill_loader

        return skill_loader
    if name == "PromptAgentMixin":
        from llm_werewolf.agent_team.agents.mixin import PromptAgentMixin

        return PromptAgentMixin
    if name in {"configure_agents_for_players", "create_react_agent"}:
        from llm_werewolf.agent_team.agents import factory

        return getattr(factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
