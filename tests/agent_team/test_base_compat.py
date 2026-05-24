from llm_werewolf.agent_team.base import DemoAgent as CanonicalDemoAgent
from llm_werewolf.agents.base import DemoAgent as AgentsDemoAgent
from llm_werewolf.core.agent import DemoAgent as CoreDemoAgent


def test_agent_base_compatibility_exports() -> None:
    assert AgentsDemoAgent is CanonicalDemoAgent
    assert CoreDemoAgent is CanonicalDemoAgent
