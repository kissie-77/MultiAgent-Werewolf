from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent as CanonicalAgent
from llm_werewolf.integration.agentscope import AgentScopeWerewolfAgent as IntegrationAgent


def test_integration_agentscope_is_compatibility_export() -> None:
    assert IntegrationAgent is CanonicalAgent
