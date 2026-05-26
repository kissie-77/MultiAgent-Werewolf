"""离线游戏正确性评测（werewolf-eval）。"""

from llm_werewolf.evaluation.correctness.models import (
    CheckResult,
    CheckSeverity,
    EvaluationSummary,
    GameRunResult,
)
from llm_werewolf.evaluation.correctness.runner import EvaluationRunner
from llm_werewolf.evaluation.correctness.scenarios import EvaluationScenario, get_scenario

__all__ = [
    "CheckResult",
    "CheckSeverity",
    "EvaluationRunner",
    "EvaluationScenario",
    "EvaluationSummary",
    "GameRunResult",
    "get_scenario",
]
