"""Compatibility exports for Agent base classes."""

from llm_werewolf.agent_team.base import (
    BaseAgent,
    DemoAgent,
    HumanAgent,
    LLMAgent,
    create_agent,
)

__all__ = ["BaseAgent", "DemoAgent", "HumanAgent", "LLMAgent", "create_agent"]
