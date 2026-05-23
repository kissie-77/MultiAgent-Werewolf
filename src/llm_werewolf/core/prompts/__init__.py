"""统一中文提示词与结构化行动选择。"""

from llm_werewolf.core.prompts.game import GamePrompts, PlanStrategies
from llm_werewolf.core.prompts.identity import IDENTITY_PROMPTS, format_identity_prompt
from llm_werewolf.core.prompts.manager import PromptManager
from llm_werewolf.core.prompts.selector import ActionSelector
from llm_werewolf.core.prompts.system import SYSTEM_PROMPT

__all__ = [
    "ActionSelector",
    "GamePrompts",
    "IDENTITY_PROMPTS",
    "PlanStrategies",
    "PromptManager",
    "SYSTEM_PROMPT",
    "format_identity_prompt",
]
