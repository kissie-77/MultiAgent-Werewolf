"""Task 3: concurrent runs get isolated provider-event log handlers."""

from __future__ import annotations

import json
import logging

from llm_werewolf.observability.core.runtime_log import (
    set_current_run,
    attach_run_log_handler,
    detach_run_log_handler,
)


def _count_lines(path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def test_two_runs_do_not_cross_contaminate(tmp_path) -> None:
    dir_a = tmp_path / "runA"
    dir_b = tmp_path / "runB"
    attach_run_log_handler(dir_a)
    attach_run_log_handler(dir_b)
    logger = logging.getLogger("llm_werewolf.test")
    try:
        set_current_run(str(dir_a))
        logger.warning("provider 429 rate limit hit")
        set_current_run(str(dir_b))
        logger.warning("provider 429 rate limit hit")
    finally:
        set_current_run(None)
        detach_run_log_handler(dir_a)
        detach_run_log_handler(dir_b)

    assert _count_lines(dir_a / "provider_events.jsonl") == 1
    assert _count_lines(dir_b / "provider_events.jsonl") == 1
    payload = json.loads((dir_a / "provider_events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert payload["kind"] == "provider_429"


def test_detach_one_run_leaves_other_active(tmp_path) -> None:
    dir_a = tmp_path / "runA"
    dir_b = tmp_path / "runB"
    attach_run_log_handler(dir_a)
    attach_run_log_handler(dir_b)
    logger = logging.getLogger("llm_werewolf.test")
    try:
        detach_run_log_handler(dir_a)
        set_current_run(str(dir_b))
        logger.warning("provider 429 rate limit hit")
    finally:
        set_current_run(None)
        detach_run_log_handler(dir_b)
    assert _count_lines(dir_a / "provider_events.jsonl") == 0
    assert _count_lines(dir_b / "provider_events.jsonl") == 1


def test_legacy_detach_all_still_works(tmp_path) -> None:
    dir_a = tmp_path / "runA"
    attach_run_log_handler(dir_a)
    logger = logging.getLogger("llm_werewolf.test")
    try:
        logger.warning("provider 429 rate limit hit")  # attach set current run for us
    finally:
        detach_run_log_handler()  # no-arg legacy detach-all
    assert _count_lines(dir_a / "provider_events.jsonl") == 1
