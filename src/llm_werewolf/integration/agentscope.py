"""Compatibility export for the AgentScope player implementation.

The canonical implementation lives in
``llm_werewolf.agent_team.agentscope_agent``.
"""

from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent

__all__ = ["AgentScopeWerewolfAgent"]
