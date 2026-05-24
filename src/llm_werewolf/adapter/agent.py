"""AgentScope Agent compatibility export.

The canonical AgentScope implementation lives in
``llm_werewolf.agent_team.agentscope_agent``.  This module is kept so existing
imports from ``llm_werewolf.adapter.agent`` continue to work during the
architecture migration.
"""

from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent

__all__ = ["AgentScopeWerewolfAgent"]
