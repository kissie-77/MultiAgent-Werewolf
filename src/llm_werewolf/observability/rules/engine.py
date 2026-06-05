"""阈值规则引擎：8 项 Phase 1 优先指标。"""

from __future__ import annotations

from typing import Any

from llm_werewolf.evaluation.core.models import CheckResult
from llm_werewolf.observability.core.config import ObservabilityConfig, RuleConfig
from llm_werewolf.observability.core.models import AlertEvent, AlertSeverity
from llm_werewolf.observability.core.runtime_log import count_provider_events


def _rule_enabled(config: ObservabilityConfig, name: str) -> RuleConfig | None:
    rule = config.rules.get(name)
    if rule is None or not rule.enabled:
        return None
    return rule


def _count_error_events(checks: list[CheckResult]) -> int:
    return sum(
        1
        for check in checks
        if not check.passed and check.checker == "RuntimeErrorEventChecker"
    )


def _count_vote_timeouts(checks: list[CheckResult]) -> int:
    count = 0
    for check in checks:
        if check.passed or check.checker != "RuntimeErrorEventChecker":
            continue
        error_type = str(check.data.get("error_type") or "")
        message = check.message.lower()
        if error_type == "TimeoutError" or "timeout" in message:
            count += 1
    return count


def _count_provider_429(checks: list[CheckResult]) -> int:
    count = 0
    for check in checks:
        if check.passed:
            continue
        blob = f"{check.message} {check.data}".lower()
        if "429" in blob or "rate limit" in blob or "ratelimit" in blob:
            count += 1
    return count


def evaluate_run_signals(
    signals: dict[str, Any],
    config: ObservabilityConfig,
) -> list[AlertEvent]:
    run_id = str(signals.get("run_id") or "unknown")
    meta = signals.get("run_meta") or {}
    post_game = signals.get("post_game") or {}
    checks: list[CheckResult] = signals.get("checks") or []
    alerts: list[AlertEvent] = []

    status = str(meta.get("status") or "").lower()
    if status == "failed" and _rule_enabled(config, "run_failed"):
        rule = config.rules["run_failed"]
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="run_meta",
                severity=rule.severity,
                code="run_failed",
                message=str(meta.get("error") or "run status failed"),
                context={"status": status},
            )
        )

    post_game_status = str(post_game.get("post_game_status") or meta.get("post_game_status") or "")
    failed_steps = post_game.get("failed_steps") or []
    if (
        post_game_status == "failed"
        or failed_steps
        or post_game.get("pipeline_error")
    ) and _rule_enabled(config, "post_game_failed"):
        rule = config.rules["post_game_failed"]
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="post_game",
                severity=rule.severity,
                code="post_game_failed",
                message=str(post_game.get("pipeline_error") or f"{len(failed_steps)} step(s) failed"),
                context={
                    "post_game_status": post_game_status or "failed",
                    "failed_steps": failed_steps,
                },
            )
        )

    error_count = _count_error_events(checks)
    rule = _rule_enabled(config, "error_events_per_run")
    if rule and rule.threshold is not None and error_count > rule.threshold:
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="events",
                severity=rule.severity,
                code="error_events_per_run",
                message=f"{error_count} runtime ERROR events (threshold {rule.threshold})",
                context={"error_count": error_count, "threshold": rule.threshold},
            )
        )

    analysis_mode = str(post_game.get("analysis_mode") or "")
    if (
        analysis_mode == "failed"
        and _rule_enabled(config, "llm_replay_failed")
    ):
        rule = config.rules["llm_replay_failed"]
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="post_game",
                severity=rule.severity,
                code="llm_replay_failed",
                message="post_game_analysis mode=failed",
                context={"analysis_mode": analysis_mode},
            )
        )

    timeout_count = _count_vote_timeouts(checks)
    rule = _rule_enabled(config, "vote_timeout_per_run")
    if rule and rule.threshold is not None and timeout_count > rule.threshold:
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="events",
                severity=rule.severity,
                code="vote_timeout_per_run",
                message=f"{timeout_count} timeout-related ERROR events (threshold {rule.threshold})",
                context={"timeout_count": timeout_count, "threshold": rule.threshold},
            )
        )

    gave_up_count = sum(
        1
        for check in checks
        if not check.passed and "structured_invoke_gave_up" in check.message.lower()
    )
    provider_events = signals.get("provider_events") or []
    gave_up_count += count_provider_events(provider_events, "structured_invoke_gave_up")
    rule = _rule_enabled(config, "structured_invoke_gave_up")
    if rule and rule.threshold is not None and gave_up_count > rule.threshold:
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="events",
                severity=rule.severity,
                code="structured_invoke_gave_up",
                message=f"{gave_up_count} structured invoke gave up signals (threshold {rule.threshold})",
                context={"count": gave_up_count, "threshold": rule.threshold},
            )
        )

    burst_429 = _count_provider_429(checks)
    burst_429 += count_provider_events(provider_events, "provider_429")
    rule = _rule_enabled(config, "provider_429_burst")
    if rule and rule.threshold is not None and burst_429 >= rule.threshold:
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="events",
                severity=rule.severity,
                code="provider_429_burst",
                message=f"{burst_429} provider 429/rate-limit signals (threshold {rule.threshold})",
                context={"count": burst_429, "threshold": rule.threshold},
            )
        )

    fallback_count = count_provider_events(provider_events, "agent_fallback")
    rule = _rule_enabled(config, "agent_fallback_per_run")
    if rule and rule.threshold is not None and fallback_count > rule.threshold:
        alerts.append(
            AlertEvent(
                run_id=run_id,
                source="agent_team",
                severity=rule.severity,
                code="agent_fallback_per_run",
                message=f"{fallback_count} agent fallback events (threshold {rule.threshold})",
                context={"count": fallback_count, "threshold": rule.threshold},
            )
        )

    return alerts


class RuleEngine:
    """面向对象的规则评估入口。"""

    def __init__(self, config: ObservabilityConfig | None = None) -> None:
        self._config = config or ObservabilityConfig.from_env()

    def evaluate(self, signals: dict[str, Any]) -> list[AlertEvent]:
        return evaluate_run_signals(signals, self._config)
