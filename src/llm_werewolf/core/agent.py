"""向后兼容的重导出；请优先使用 ``llm_werewolf.agents``。"""

from llm_werewolf.agents.base import (
    BaseAgent,
    DemoAgent,
    HumanAgent,
    LLMAgent,
    create_agent,
)

__all__ = ["BaseAgent", "DemoAgent", "HumanAgent", "LLMAgent", "create_agent"]
