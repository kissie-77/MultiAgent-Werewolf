"""扫描 artifacts 目录并分发告警。"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

import fire

from llm_werewolf.paths import RUNS_DIR, EVAL_RUNS_DIR
from llm_werewolf.observability.core.config import load_config
from llm_werewolf.observability.core.models import AlertEvent, AlertSeverity
from llm_werewolf.observability.core.dispatcher import AlertDispatcher, get_dispatcher


def _parse_since(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip().lower()
    if text.endswith("h") and text[:-1].isdigit():
        return datetime.now() - timedelta(hours=int(text[:-1]))
    if text.endswith("d") and text[:-1].isdigit():
        return datetime.now() - timedelta(days=int(text[:-1]))
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _run_dirs(root: Path, *, since: datetime | None) -> list[Path]:
    if not root.is_dir():
        return []
    dirs = [path for path in root.iterdir() if path.is_dir()]
    if since is None:
        return sorted(dirs)
    selected: list[Path] = []
    for path in dirs:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if mtime >= since:
            selected.append(path)
    return sorted(selected)


def _collect_all(
    runs_dir: Path,
    eval_runs_dir: Path,
    *,
    since: datetime | None,
) -> list[Path]:
    paths = _run_dirs(runs_dir, since=since)
    eval_root = eval_runs_dir
    if eval_root.is_dir():
        for batch in eval_root.iterdir():
            if not batch.is_dir():
                continue
            games = batch / "games"
            if games.is_dir():
                paths.extend(_run_dirs(games, since=since))
            else:
                paths.extend(_run_dirs(batch, since=since))
    return paths


async def _watch_async(
    *,
    runs_dir: str = str(RUNS_DIR),
    eval_runs_dir: str = str(EVAL_RUNS_DIR),
    since: str | None = None,
    push: bool = False,
    fail_on_critical: bool = False,
    config_path: str | None = None,
) -> str:
    config = load_config(Path(config_path) if config_path else None)
    dispatcher = get_dispatcher(config) if push else AlertDispatcher(config, notifiers=[])
    since_dt = _parse_since(since)
    run_paths = _collect_all(Path(runs_dir), Path(eval_runs_dir), since=since_dt)

    all_alerts: list[AlertEvent] = []
    for run_dir in run_paths:
        emitted = await dispatcher.emit_from_run_dir(run_dir)
        all_alerts.extend(emitted)

    summary = {
        "schema": "watch_summary_v1",
        "scanned_runs": len(run_paths),
        "alert_count": len(all_alerts),
        "alerts": [event.model_dump(mode="json") for event in all_alerts],
    }
    out_dir = config.alerts_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "alerts.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if fail_on_critical and any(event.severity == AlertSeverity.CRITICAL for event in all_alerts):
        raise SystemExit(1)
    return str(out_path)


def main(
    runs_dir: str = str(RUNS_DIR),
    eval_runs_dir: str = str(EVAL_RUNS_DIR),
    since: str | None = None,
    push: bool = False,
    fail_on_critical: bool = False,
    config_path: str | None = None,
) -> str:
    return asyncio.run(
        _watch_async(
            runs_dir=runs_dir,
            eval_runs_dir=eval_runs_dir,
            since=since,
            push=push,
            fail_on_critical=fail_on_critical,
            config_path=config_path,
        )
    )


def entry() -> None:
    fire.Fire(main)


if __name__ == "__main__":
    entry()
