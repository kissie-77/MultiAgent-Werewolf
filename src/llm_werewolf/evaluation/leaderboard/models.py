"""Data models for leaderboard entries and A/B reports."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from dataclasses import field, asdict, dataclass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LeaderboardEntry:
    schema: str
    version_id: str
    model: str
    prompt_version: str
    skill_version: str
    scenario: str
    games: int
    completed_games: int
    completion_rate: float
    win_rate: float
    avg_rounds: float
    avg_mvp_score: float | None
    avg_benefit_score: float | None
    avg_intention_score: float | None
    information_leak_count: int
    phase_order_violation_count: int
    role_skill_violation_count: int
    top_errors: list[str]
    source_run_dir: str
    generated_at: str = field(default_factory=utc_now_iso)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ABReport:
    schema: str
    version_a: str
    version_b: str
    games_a: int
    games_b: int
    win_rate_a: float
    win_rate_b: float
    win_rate_delta: float
    avg_mvp_score_a: float | None
    avg_mvp_score_b: float | None
    avg_benefit_score_a: float | None
    avg_benefit_score_b: float | None
    avg_intention_score_a: float | None
    avg_intention_score_b: float | None
    completion_rate_a: float
    completion_rate_b: float
    wins_a: int
    wins_b: int
    win_rate_ci_a: tuple[float, float]
    win_rate_ci_b: tuple[float, float]
    win_rate_p_value: float | None
    win_rate_significant: bool
    significance_method: str
    recommendation: str
    summary: str
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
