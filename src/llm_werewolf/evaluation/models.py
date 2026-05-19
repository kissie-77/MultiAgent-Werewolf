from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class CheckSeverity(str, Enum):
    """Severity levels for evaluation findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CheckResult(BaseModel):
    """Result from a correctness checker."""

    checker: str
    passed: bool
    message: str
    severity: CheckSeverity = CheckSeverity.ERROR
    data: dict[str, Any] = Field(default_factory=dict)


class GameRunResult(BaseModel):
    """Outcome and findings for one evaluated game."""

    game_id: str
    scenario_name: str
    seed: int
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
        """Count failed checker results."""
        return sum(1 for check in self.checks if not check.passed)

    @computed_field
    @property
    def has_failures(self) -> bool:
        """Whether this run has a crash, timeout, or failed check."""
        return self.crashed or self.timed_out or self.failure_count > 0


class EvaluationSummary(BaseModel):
    """Aggregated metrics for an evaluation batch."""

    total_games: int
    completed_games: int = 0
    crashed_games: int = 0
    timeout_games: int = 0
    avg_rounds_per_game: float = 0.0
    role_skill_violation_count: int = 0
    information_leak_count: int = 0
    victory_rule_violation_count: int = 0
    phase_order_violation_count: int = 0
    invalid_action_count: int = 0
    exception_count_by_role: dict[str, int] = Field(default_factory=dict)
    exception_count_by_phase: dict[str, int] = Field(default_factory=dict)
    missing_structured_event_count: int = 0
    top_errors: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def completion_rate(self) -> float:
        """Completed games divided by total games."""
        return self.completed_games / self.total_games if self.total_games else 0.0

    @computed_field
    @property
    def crash_rate(self) -> float:
        """Crashed games divided by total games."""
        return self.crashed_games / self.total_games if self.total_games else 0.0

    @computed_field
    @property
    def timeout_rate(self) -> float:
        """Timed-out games divided by total games."""
        return self.timeout_games / self.total_games if self.total_games else 0.0
