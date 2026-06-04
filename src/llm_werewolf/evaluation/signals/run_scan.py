"""对已有 run 目录运行 checker 子集。"""

from __future__ import annotations

import json
from pathlib import Path

from llm_werewolf.evaluation.core.checkers import (
    AsyncFlowChecker,
    DecisionConsistencyChecker,
    InformationIsolationChecker,
    RoleSkillChecker,
    VictoryCheckerEvaluator,
)
from llm_werewolf.evaluation.core.models import CheckResult
from llm_werewolf.evaluation.post_game.event_adapter import event_from_dict
from llm_werewolf.game_runtime.types import Event
from llm_werewolf.game_runtime.types.enums import EventType


def _read_events_jsonl(path: Path) -> list[Event]:
    if not path.is_file():
        return []
    events: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(raw, dict):
            continue
        event = event_from_dict(raw)
        if event is not None:
            events.append(event)
    return events


def _error_event_checks(events: list[Event]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for event in events:
        if event.event_type != EventType.ERROR:
            continue
        role_name = event.data.get("role") or event.data.get("role_name")
        results.append(
            CheckResult(
                checker="RuntimeErrorEventChecker",
                passed=False,
                message=event.data.get("error", event.message),
                data={
                    "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
                    "round_number": event.round_number,
                    "player_id": event.data.get("player_id"),
                    "role_name": role_name,
                    "error_type": event.data.get("error_type"),
                },
            )
        )
    return results


def _final_winner(events: list[Event]) -> str | None:
    for event in reversed(events):
        if event.event_type == EventType.GAME_ENDED:
            winner = event.data.get("winner")
            if winner:
                return str(winner)
    return None


def scan_run_dir(
    run_dir: Path,
    *,
    include_heavy_checkers: bool = True,
) -> list[CheckResult]:
    """扫描 run 目录并返回 checker 结果（含 RuntimeErrorEventChecker）。"""
    run_dir = Path(run_dir)
    events = _read_events_jsonl(run_dir / "events.jsonl")
    if not events:
        return []

    final_winner = _final_winner(events)
    checks: list[CheckResult] = []

    if include_heavy_checkers:
        checkers: list[tuple[object, dict]] = [
            (RoleSkillChecker(), {"events": events}),
            (InformationIsolationChecker(), {"events": events, "observations_by_player": {}}),
            (VictoryCheckerEvaluator(), {"events": events, "final_winner": final_winner}),
            (AsyncFlowChecker(), {"events": events}),
            (DecisionConsistencyChecker(), {"events": events}),
        ]
        for checker, kwargs in checkers:
            try:
                checks.extend(checker.check(**kwargs))  # type: ignore[attr-defined]
            except Exception as exc:
                checks.append(
                    CheckResult(
                        checker=checker.__class__.__name__,
                        passed=False,
                        message=f"Checker raised {type(exc).__name__}: {exc}",
                    )
                )

    checks.extend(_error_event_checks(events))
    return checks
