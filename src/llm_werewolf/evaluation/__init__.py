"""狼人杀评测包：正确性离线评测 + 赛后分析。

- ``evaluation.correctness`` — ``werewolf-eval`` 批量跑局与 checker
- ``evaluation.post_game`` — 对局结束后的说服分析、打分、Prompt 提案与 Skill 草案
"""

from llm_werewolf.evaluation.correctness import (
    CheckResult,
    CheckSeverity,
    EvaluationRunner,
    EvaluationScenario,
    EvaluationSummary,
    GameRunResult,
    get_scenario,
)
from llm_werewolf.evaluation.post_game import PostGameResult, run_post_game_pipeline

__all__ = [
    "CheckResult",
    "CheckSeverity",
    "EvaluationRunner",
    "EvaluationScenario",
    "EvaluationSummary",
    "GameRunResult",
    "PostGameResult",
    "get_scenario",
    "run_post_game_pipeline",
]
