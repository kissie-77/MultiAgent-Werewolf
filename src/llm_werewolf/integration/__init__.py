"""External runtime integrations (AgentScope, message adapters)."""

from llm_werewolf.integration.message import MessageAdapter, Msg

__all__ = ["AgentScopeWerewolfAgent", "MessageAdapter", "Msg"]


def __getattr__(name: str):
    if name == "AgentScopeWerewolfAgent":
        from llm_werewolf.integration.agentscope import AgentScopeWerewolfAgent

        return AgentScopeWerewolfAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
