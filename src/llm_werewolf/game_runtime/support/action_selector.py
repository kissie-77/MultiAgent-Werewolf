"""向后兼容的重导出；请优先使用 ``llm_werewolf.game_runtime.prompts``。"""

from llm_werewolf.game_runtime.prompts.selector import ActionSelector

__all__ = ["ActionSelector"]
