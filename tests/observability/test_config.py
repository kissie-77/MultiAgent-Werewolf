"""Observability config loading tests."""

from __future__ import annotations

import os
from pathlib import Path

from llm_werewolf.observability.core.config import load_config


def test_yaml_webhook_placeholder_falls_back_to_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OBS_ALERT_WEBHOOK_URL", "https://example.com/hook")
    config_path = tmp_path / "observability.yaml"
    config_path.write_text(
        """
notifiers:
  webhook:
    url: ${OBS_ALERT_WEBHOOK_URL}
""",
        encoding="utf-8",
    )
    config = load_config(config_path, alerts_dir=tmp_path / "alerts")
    assert config.webhook_url == "https://example.com/hook"


def test_yaml_webhook_placeholder_without_env_is_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OBS_ALERT_WEBHOOK_URL", raising=False)
    config_path = tmp_path / "observability.yaml"
    config_path.write_text(
        """
notifiers:
  webhook:
    url: ${OBS_ALERT_WEBHOOK_URL}
""",
        encoding="utf-8",
    )
    config = load_config(config_path, alerts_dir=tmp_path / "alerts")
    assert config.webhook_url is None
