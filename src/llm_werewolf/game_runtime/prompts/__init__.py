"""统一中文提示词与结构化行动选择。"""

from llm_werewolf.game_runtime.prompts.system import SYSTEM_PROMPT
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.game_runtime.prompts.identity import IDENTITY_PROMPTS, format_identity_prompt
from llm_werewolf.game_runtime.prompts.selector import ActionSelector

__all__ = [
    "IDENTITY_PROMPTS",
    "SYSTEM_PROMPT",
    "ActionSelector",
    "PromptManager",
    "format_identity_prompt",
]
