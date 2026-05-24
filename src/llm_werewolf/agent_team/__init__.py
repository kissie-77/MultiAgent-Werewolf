"""Multi-agent runtime integration."""

__all__ = [
    "AgentScopeWerewolfAgent",
    "BaseAgent",
    "DemoAgent",
    "HumanAgent",
    "LLMAgent",
    "PromptAgentMixin",
    "configure_agents_for_players",
    "create_react_agent",
    "create_agent",
]


def __getattr__(name: str):
    if name == "AgentScopeWerewolfAgent":
        from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent

        return AgentScopeWerewolfAgent
    if name in {"BaseAgent", "DemoAgent", "HumanAgent", "LLMAgent", "create_agent"}:
        from llm_werewolf.agent_team import base

        return getattr(base, name)
    if name == "PromptAgentMixin":
        from llm_werewolf.agent_team.mixin import PromptAgentMixin

        return PromptAgentMixin
    if name in {"configure_agents_for_players", "create_react_agent"}:
        from llm_werewolf.agent_team import factory

        return getattr(factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
