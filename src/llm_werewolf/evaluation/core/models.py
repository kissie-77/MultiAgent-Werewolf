from enum import Enum
from typing import Any

from pydantic import Field, BaseModel, computed_field


class CheckSeverity(str, Enum):
    """单条检查结果的严重程度。

    评测报告里会同时出现“提示性问题”和“会影响游戏正确性的问题”。
    用枚举固定等级，便于后续 Web 复盘页做颜色和过滤。
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CheckResult(BaseModel):
    """一个 checker 产生的一条检查结果。

    `passed=False` 表示发现了具体问题；`data` 保存可定位问题的结构化上下文，
    例如玩家、阶段、事件类型、缺失字段等。
    """

    # checker 名称用于聚合统计，例如 AsyncFlowChecker / RoleSkillChecker。
    checker: str
    # 当前检查项是否通过。失败项会进入 violation 计数。
    passed: bool
    # 人类可读摘要，会出现在 report.md 和 top_errors 中。
    message: str
    # 严重程度默认按 error 处理；信息泄露等问题可以提升为 critical。
    severity: CheckSeverity = CheckSeverity.ERROR
    # 机器可读上下文，后续 Web 复盘和调试入口主要依赖这里。
    data: dict[str, Any] = Field(default_factory=dict)


class GameRunResult(BaseModel):
    """单局评测的最终结果。

    runner 每跑完一局都会生成一个 GameRunResult。它只保存摘要，
    详细证据放在对应 game_id 目录下的 events/snapshots/errors/checks 文件中。
    """

    # 产物目录名的一部分，必须稳定，方便报告链接到单局证据。
    game_id: str
    # 场景名，例如 smoke_6p_basic 或 regression_default_demo。
    scenario_name: str
    # 本局使用的随机种子，用于复现角色洗牌和随机选择。
    seed: int
    # 是否正常结束并产生 winner。崩溃/超时即使写了文件也不算 completed。
    completed: bool
    crashed: bool = False
    timed_out: bool = False
    winner: str | None = None
    rounds_played: int = 0
    duration_seconds: float = 0.0
    error_type: str | None = None
    error_message: str | None = None
    checks: list[CheckResult] = Field(default_factory=list)

    @computed_field
    @property
    def failure_count(self) -> int:
        """统计本局失败的 checker 数量。"""
        return sum(1 for check in self.checks if not check.passed)

    @computed_field
    @property
    def has_failures(self) -> bool:
        """本局是否存在任何失败信号：崩溃、超时或 checker 失败。"""
        return self.crashed or self.timed_out or self.failure_count > 0


class EvaluationSummary(BaseModel):
    """一批评测的汇总指标。

    这个模型会直接写入 summary.json，因此字段名要保持稳定。
    新增 metric 时优先追加字段，不要轻易重命名旧字段。
    """

    # 运行规模与稳定性指标。
    total_games: int
    completed_games: int = 0
    crashed_games: int = 0
    timeout_games: int = 0
    avg_rounds_per_game: float = 0.0

    # 正确性违规指标。第一版的重点是系统正确性，不评价模型强弱。
    role_skill_violation_count: int = 0
    information_leak_count: int = 0
    victory_rule_violation_count: int = 0
    phase_order_violation_count: int = 0
    invalid_action_count: int = 0

    # 运行时错误按角色和阶段聚合，用来快速定位“哪个角色/阶段最容易炸”。
    exception_count_by_role: dict[str, int] = Field(default_factory=dict)
    exception_count_by_phase: dict[str, int] = Field(default_factory=dict)
    missing_structured_event_count: int = 0
    top_errors: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def completion_rate(self) -> float:
        """已完成局数除以总局数。"""
        return self.completed_games / self.total_games if self.total_games else 0.0

    @computed_field
    @property
    def crash_rate(self) -> float:
        """崩溃局数除以总局数。"""
        return self.crashed_games / self.total_games if self.total_games else 0.0

    @computed_field
    @property
    def timeout_rate(self) -> float:
        """超时局数除以总局数。"""
        return self.timeout_games / self.total_games if self.total_games else 0.0
