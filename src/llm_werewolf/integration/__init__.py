"""外部运行时集成（AgentScope、消息适配器）。"""

from llm_werewolf.integration.message import MessageAdapter, Msg

__all__ = ["AgentScopeWerewolfAgent", "MessageAdapter", "Msg"]


def __getattr__(name: str):
    if name == "AgentScopeWerewolfAgent":
        from llm_werewolf.integration.agentscope import AgentScopeWerewolfAgent

        return AgentScopeWerewolfAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
