"""Task 4: create_agent 工厂应为 model=="web-human" 返回 WebHumanAgent。"""

from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.agent_team.agents.base import create_agent
from llm_werewolf.agent_team.agents.web_human_agent import WebHumanAgent


def test_create_agent_returns_web_human():
    agent = create_agent(PlayerConfig(name="P1", model="web-human"))
    assert isinstance(agent, WebHumanAgent)
    assert agent.name == "P1"
    assert agent.model == "web-human"
