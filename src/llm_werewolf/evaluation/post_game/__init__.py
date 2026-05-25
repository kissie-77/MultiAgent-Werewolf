"""对局结束后的复盘、阵营说服分析与 Prompt 提案（JSON，不写入运行时）。"""

from llm_werewolf.evaluation.post_game.pipeline import PostGameResult, run_post_game_pipeline

__all__ = ["PostGameResult", "run_post_game_pipeline"]
