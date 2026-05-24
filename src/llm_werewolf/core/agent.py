"""向后兼容的重导出；请优先使用 ``llm_werewolf.agent_team``。"""

from llm_werewolf.agent_team.base import (
    BaseAgent,
    DemoAgent,
    HumanAgent,
    LLMAgent,
    create_agent,
)

__all__ = ["BaseAgent", "DemoAgent", "HumanAgent", "LLMAgent", "create_agent"]
