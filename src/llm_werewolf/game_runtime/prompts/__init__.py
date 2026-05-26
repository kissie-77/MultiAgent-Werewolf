"""统一中文提示词与结构化行动选择。"""

from llm_werewolf.game_runtime.prompts.identity import IDENTITY_PROMPTS, format_identity_prompt
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.game_runtime.prompts.selector import ActionSelector
from llm_werewolf.game_runtime.prompts.system import SYSTEM_PROMPT

__all__ = [
    "ActionSelector",
    "IDENTITY_PROMPTS",
    "PromptManager",
    "SYSTEM_PROMPT",
    "format_identity_prompt",
]
