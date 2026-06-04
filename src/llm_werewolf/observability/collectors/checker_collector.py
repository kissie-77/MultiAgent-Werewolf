"""包装 evaluation checkers 为告警事件。"""

from __future__ import annotations

from typing import Any

from llm_werewolf.evaluation.core.models import CheckResult, CheckSeverity
from llm_werewolf.observability.config import ObservabilityConfig
from llm_werewolf.observability.models import AlertEvent, AlertSeverity


def collect_checker_alerts(
    signals: dict[str, Any],
    config: ObservabilityConfig,
) -> list[AlertEvent]:
    rule = config.rules.get("checker_critical")
    if rule is None or not rule.enabled:
        return []

    run_id = str(signals.get("run_id") or "unknown")
    checks: list[CheckResult] = signals.get("checks") or []
    alerts: list[AlertEvent] = []
    for check in checks:
        if check.passed:
            continue
        if check.severity != CheckSeverity.CRITICAL:
            continue
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="checker",
                severity=AlertSeverity.CRITICAL,
                code="checker_critical",
                message=f"{check.checker}: {check.message}",
                context={
                    "checker": check.checker,
                    "data": check.data,
                },
            )
        )
    return alerts
