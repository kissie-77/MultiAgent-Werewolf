"""Helpers for estimating and comparing game wall-clock time."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RoundtableTimeEstimate:
    num_players: int
    vote_intention_concurrency: int
    logical_calls: int
    vote_intention_logical_calls: int
    wall_seconds: float


@dataclass(frozen=True)
class RoundtableTimeComparison:
    before: RoundtableTimeEstimate
    after: RoundtableTimeEstimate
    speedup: float
    saved_seconds: float
    saved_percent: float


@dataclass(frozen=True)
class EventLogDurationComparison:
    before_seconds: float
    after_seconds: float
    speedup: float
    saved_seconds: float
    saved_percent: float


def estimate_roundtable_time(
    *,
    num_players: int,
    vote_intention_concurrency: int,
    seconds_per_http: float,
    http_round_trips_per_decision: int = 1,
) -> RoundtableTimeEstimate:
    """Estimate one roundtable's wall time from call topology and API latency."""
    if num_players < 1:
        msg = "num_players must be positive"
        raise ValueError(msg)
    if vote_intention_concurrency < 1:
        msg = "vote_intention_concurrency must be positive"
        raise ValueError(msg)
    if seconds_per_http < 0:
        msg = "seconds_per_http must be non-negative"
        raise ValueError(msg)
    if http_round_trips_per_decision < 1:
        msg = "http_round_trips_per_decision must be positive"
        raise ValueError(msg)

    logical_calls = num_players * num_players + 2 * num_players
    vote_intention_logical_calls = num_players * num_players + num_players
    batch_waves = math.ceil(num_players / vote_intention_concurrency)
    logical_call_seconds = seconds_per_http * http_round_trips_per_decision

    speech_seconds = num_players * logical_call_seconds
    initial_intention_seconds = batch_waves * logical_call_seconds
    after_speech_intention_seconds = num_players * batch_waves * logical_call_seconds
    wall_seconds = (
        speech_seconds
        + initial_intention_seconds
        + after_speech_intention_seconds
    )
    return RoundtableTimeEstimate(
        num_players=num_players,
        vote_intention_concurrency=vote_intention_concurrency,
        logical_calls=logical_calls,
        vote_intention_logical_calls=vote_intention_logical_calls,
        wall_seconds=wall_seconds,
    )


def compare_roundtable_parallelism(
    *,
    num_players: int,
    before_concurrency: int,
    after_concurrency: int,
    seconds_per_http: float,
    http_round_trips_per_decision: int = 1,
) -> RoundtableTimeComparison:
    """Compare one roundtable before and after vote-intention parallelism."""
    before = estimate_roundtable_time(
        num_players=num_players,
        vote_intention_concurrency=before_concurrency,
        seconds_per_http=seconds_per_http,
        http_round_trips_per_decision=http_round_trips_per_decision,
    )
    after = estimate_roundtable_time(
        num_players=num_players,
        vote_intention_concurrency=after_concurrency,
        seconds_per_http=seconds_per_http,
        http_round_trips_per_decision=http_round_trips_per_decision,
    )
    return _roundtable_comparison(before, after)


def compare_event_log_durations(
    before_events_path: str | Path,
    after_events_path: str | Path,
) -> EventLogDurationComparison:
    """Compare measured durations using first and last event timestamps."""
    before_seconds = event_log_duration_seconds(before_events_path)
    after_seconds = event_log_duration_seconds(after_events_path)
    saved_seconds = before_seconds - after_seconds
    speedup = before_seconds / after_seconds if after_seconds else math.inf
    saved_percent = (saved_seconds / before_seconds * 100) if before_seconds else 0.0
    return EventLogDurationComparison(
        before_seconds=before_seconds,
        after_seconds=after_seconds,
        speedup=speedup,
        saved_seconds=saved_seconds,
        saved_percent=saved_percent,
    )


def event_log_duration_seconds(events_path: str | Path) -> float:
    """Return elapsed seconds between the first and last timestamp in a JSONL log."""
    timestamps: list[datetime] = []
    path = Path(events_path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        timestamp = payload.get("timestamp")
        if timestamp:
            timestamps.append(_parse_timestamp(str(timestamp)))

    if len(timestamps) < 2:
        return 0.0
    return (timestamps[-1] - timestamps[0]).total_seconds()


def _roundtable_comparison(
    before: RoundtableTimeEstimate,
    after: RoundtableTimeEstimate,
) -> RoundtableTimeComparison:
    saved_seconds = before.wall_seconds - after.wall_seconds
    speedup = before.wall_seconds / after.wall_seconds if after.wall_seconds else math.inf
    saved_percent = (
        saved_seconds / before.wall_seconds * 100 if before.wall_seconds else 0.0
    )
    return RoundtableTimeComparison(
        before=before,
        after=after,
        speedup=speedup,
        saved_seconds=saved_seconds,
        saved_percent=saved_percent,
    )


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
