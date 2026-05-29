from llm_werewolf.agent_team.agents.base import BaseAgent, DemoAgent
from llm_werewolf.agent_team.agents.human_interactive_agent import HumanInteractiveAgent


def test_agent_team_base_exports_agent_types() -> None:
    assert issubclass(DemoAgent, BaseAgent)
    assert issubclass(HumanInteractiveAgent, BaseAgent)
