"""从 run 产物与 evaluation 信号生成 AlertEvent。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

from llm_werewolf.observability.core.config import ObservabilityConfig
from llm_werewolf.observability.rules.engine import evaluate_run_signals
from llm_werewolf.evaluation.signals.run_scan import scan_run_dir
from llm_werewolf.observability.core.runtime_log import load_provider_events
from llm_werewolf.evaluation.signals.post_game_signals import load_post_game_signals
from llm_werewolf.observability.collectors.checker_collector import collect_checker_alerts

if TYPE_CHECKING:
    from llm_werewolf.observability.core.models import AlertEvent


def _read_run_meta(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "run_meta.json"
    if not path.is_file():
        return {}
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def collect_run_signals(run_dir: Path) -> dict[str, Any]:
    """归一化单场 run 的可观测信号。"""
    run_dir = Path(run_dir)
    meta = _read_run_meta(run_dir)
    post_game = load_post_game_signals(run_dir)
    checks = scan_run_dir(run_dir, include_heavy_checkers=False)
    return {
        "run_id": str(meta.get("run_id") or run_dir.name),
        "run_dir": str(run_dir),
        "run_meta": meta,
        "post_game": post_game,
        "checks": checks,
        "provider_events": load_provider_events(run_dir),
    }


class RunArtifactCollector:
    """从 run 目录采集并评估告警。"""

    def __init__(self, config: ObservabilityConfig | None = None) -> None:
        self._config = config or ObservabilityConfig.from_env()

    def collect(self, run_dir: Path) -> list[AlertEvent]:
        signals = collect_run_signals(run_dir)
        alerts = evaluate_run_signals(signals, self._config)
        alerts.extend(collect_checker_alerts(signals, self._config))
        return alerts
