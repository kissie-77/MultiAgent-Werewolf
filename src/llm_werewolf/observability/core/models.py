"""告警事件模型，severity 对齐 evaluation CheckSeverity。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from llm_werewolf.evaluation.core.models import CheckSeverity


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @classmethod
    def from_check(cls, severity: CheckSeverity) -> AlertSeverity:
        return cls(severity.value)

    def rank(self) -> int:
        order = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.ERROR: 2,
            AlertSeverity.CRITICAL: 3,
        }
        return order[self]

    def meets_minimum(self, minimum: AlertSeverity) -> bool:
        return self.rank() >= minimum.rank()


class AlertEvent(BaseModel):
    run_id: str
    source: str
    severity: AlertSeverity
    code: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"),
    )

    def dedupe_key(self) -> str:
        return f"{self.run_id}:{self.code}"
