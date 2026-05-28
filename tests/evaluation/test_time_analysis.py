import json
from datetime import datetime, timedelta

from llm_werewolf.evaluation.time_analysis import (
    compare_event_log_durations,
    compare_roundtable_parallelism,
    estimate_roundtable_time,
)


def test_estimate_roundtable_time_models_serial_vote_intentions() -> None:
    estimate = estimate_roundtable_time(
        num_players=6,
        vote_intention_concurrency=1,
        seconds_per_http=10,
        http_round_trips_per_decision=2,
    )

    assert estimate.logical_calls == 48
    assert estimate.vote_intention_logical_calls == 42
    assert estimate.wall_seconds == 960


def test_compare_roundtable_parallelism_calculates_speedup() -> None:
    comparison = compare_roundtable_parallelism(
        num_players=6,
        before_concurrency=1,
        after_concurrency=6,
        seconds_per_http=10,
        http_round_trips_per_decision=2,
    )

    assert comparison.before.wall_seconds == 960
    assert comparison.after.wall_seconds == 260
    assert round(comparison.speedup, 2) == 3.69
    assert round(comparison.saved_percent, 1) == 72.9


def test_compare_event_log_durations_reads_first_and_last_timestamp(tmp_path) -> None:
    before = tmp_path / "before.jsonl"
    after = tmp_path / "after.jsonl"
    start = datetime(2026, 5, 28, 12, 0, 0)

    before.write_text(
        "\n".join(
            [
                json.dumps({"timestamp": start.isoformat()}),
                json.dumps({"timestamp": (start + timedelta(seconds=100)).isoformat()}),
            ],
        ),
        encoding="utf-8",
    )
    after.write_text(
        "\n".join(
            [
                json.dumps({"timestamp": start.isoformat()}),
                json.dumps({"timestamp": (start + timedelta(seconds=25)).isoformat()}),
            ],
        ),
        encoding="utf-8",
    )

    comparison = compare_event_log_durations(before, after)

    assert comparison.before_seconds == 100
    assert comparison.after_seconds == 25
    assert comparison.speedup == 4
    assert comparison.saved_percent == 75
