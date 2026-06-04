"""告警配置：环境变量 + 可选 YAML。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_werewolf.observability.models import AlertSeverity


def _parse_severity(raw: str | None, default: AlertSeverity) -> AlertSeverity:
    if not raw:
        return default
    try:
        return AlertSeverity(str(raw).strip().lower())
    except ValueError:
        return default


def _expand_env(value: str) -> str | None:
    """展开 ${VAR} 占位符；未设置或空值时返回 None。"""
    text = value.strip()
    if text.startswith("${") and text.endswith("}"):
        key = text[2:-1]
        return os.environ.get(key) or None
    return text or None


@dataclass
class RuleConfig:
    enabled: bool = True
    threshold: int | None = None
    severity: AlertSeverity = AlertSeverity.WARNING


@dataclass
class ObservabilityConfig:
    webhook_url: str | None = None
    min_severity: AlertSeverity = AlertSeverity.WARNING
    dedupe_ttl_seconds: int = 300
    alerts_dir: Path = field(default_factory=lambda: Path("artifacts/alerts"))
    rules: dict[str, RuleConfig] = field(default_factory=dict)

    @classmethod
    def from_env(cls, *, alerts_dir: Path | None = None) -> ObservabilityConfig:
        rules = {
            "run_failed": RuleConfig(enabled=True, severity=AlertSeverity.ERROR),
            "post_game_failed": RuleConfig(enabled=True, severity=AlertSeverity.ERROR),
            "error_events_per_run": RuleConfig(
                enabled=True,
                threshold=3,
                severity=AlertSeverity.WARNING,
            ),
            "checker_critical": RuleConfig(enabled=True, severity=AlertSeverity.CRITICAL),
            "llm_replay_failed": RuleConfig(enabled=True, severity=AlertSeverity.WARNING),
            "vote_timeout_per_run": RuleConfig(
                enabled=True,
                threshold=2,
                severity=AlertSeverity.WARNING,
            ),
            "structured_invoke_gave_up": RuleConfig(
                enabled=True,
                threshold=10,
                severity=AlertSeverity.WARNING,
            ),
            "provider_429_burst": RuleConfig(
                enabled=True,
                threshold=3,
                severity=AlertSeverity.ERROR,
            ),
            "agent_fallback_per_run": RuleConfig(
                enabled=True,
                threshold=5,
                severity=AlertSeverity.WARNING,
            ),
        }
        return cls(
            webhook_url=os.environ.get("OBS_ALERT_WEBHOOK_URL") or None,
            min_severity=_parse_severity(
                os.environ.get("OBS_ALERT_MIN_SEVERITY"),
                AlertSeverity.WARNING,
            ),
            dedupe_ttl_seconds=int(os.environ.get("OBS_ALERT_DEDUPE_TTL", "300")),
            alerts_dir=alerts_dir or Path(os.environ.get("OBS_ALERTS_DIR", "artifacts/alerts")),
            rules=rules,
        )


def load_config(path: Path | None = None, *, alerts_dir: Path | None = None) -> ObservabilityConfig:
    """加载配置；YAML 可选，未安装 PyYAML 时仅读 env。"""
    config = ObservabilityConfig.from_env(alerts_dir=alerts_dir)
    if path is None:
        default = Path("configs/observability.yaml")
        path = default if default.is_file() else None
    if path is None or not path.is_file():
        return config

    try:
        import yaml
    except ImportError:
        return config

    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    notifiers = raw.get("notifiers") or {}
    webhook = notifiers.get("webhook") or {}
    if webhook.get("url"):
        expanded = _expand_env(str(webhook["url"]))
        if expanded:
            config.webhook_url = expanded
    if webhook.get("min_severity"):
        config.min_severity = _parse_severity(str(webhook["min_severity"]), config.min_severity)

    dispatcher = raw.get("dispatcher") or {}
    if dispatcher.get("dedupe_ttl_seconds") is not None:
        config.dedupe_ttl_seconds = int(dispatcher["dedupe_ttl_seconds"])

    rules_raw = raw.get("rules") or {}
    for name, body in rules_raw.items():
        if not isinstance(body, dict):
            continue
        existing = config.rules.get(name, RuleConfig())
        if "enabled" in body:
            existing.enabled = bool(body["enabled"])
        if body.get("threshold") is not None:
            existing.threshold = int(body["threshold"])
        if body.get("severity"):
            existing.severity = _parse_severity(str(body["severity"]), existing.severity)
        config.rules[name] = existing
    return config
