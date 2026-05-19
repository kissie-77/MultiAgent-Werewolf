"""狼人杀离线正确性评测模块。

这个包只负责“测游戏系统是否正确”，不负责真实模型强弱评测。
它通过 runner 批量跑局，通过 recorder 保留证据，通过 checkers 发现问题，
最后由 metrics/reporter 聚合成机器可读和人类可读的报告。
"""

from llm_werewolf.evaluation.models import (
    CheckResult,
    CheckSeverity,
    EvaluationSummary,
    GameRunResult,
)

__all__ = [
    "CheckResult",
    "CheckSeverity",
    "EvaluationSummary",
    "GameRunResult",
]
