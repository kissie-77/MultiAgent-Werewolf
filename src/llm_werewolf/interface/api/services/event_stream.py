"""In-process SSE fan-out of live game events, keyed by run_id."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
import asyncio
import contextlib

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import AsyncIterator

_MAX_QUEUE = 2000


class EventBroadcaster:
    """Fan out serialized game events to live SSE subscribers for one run.

    ``publish`` is invoked synchronously from the engine ``on_event`` hook
    (inside the game's asyncio task). Each event gets a monotonically
    increasing 1-based ``event_id`` matching its line number in
    ``events.jsonl`` so clients can resume via ``Last-Event-ID``.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any] | None]] = set()
        self._count = 0
        self._closed = False

    @property
    def count(self) -> int:
        return self._count

    @property
    def closed(self) -> bool:
        return self._closed

    def publish(self, event: dict[str, Any]) -> int:
        """Stamp an event_id and fan out to subscribers. Sync-safe (put_nowait)."""
        self._count += 1
        enriched = {**event, "event_id": self._count}
        for q in list(self._subscribers):
            # Slow consumer: drop the live item; it can reconnect and
            # replay missed events from events.jsonl via Last-Event-ID.
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(enriched)
        return self._count

    def close(self) -> None:
        """Signal end-of-stream (game finished) to all subscribers."""
        self._closed = True
        for q in list(self._subscribers):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(None)

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        """Yield live events until ``close()``. Always unsubscribes on exit."""
        q: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=_MAX_QUEUE)
        self._subscribers.add(q)
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                yield item
        finally:
            self._subscribers.discard(q)


_registry: dict[str, EventBroadcaster] = {}


def get_or_create_broadcaster(run_id: str) -> EventBroadcaster:
    b = _registry.get(run_id)
    if b is None:
        b = EventBroadcaster()
        _registry[run_id] = b
    return b


def get_broadcaster(run_id: str) -> EventBroadcaster | None:
    return _registry.get(run_id)


def remove_broadcaster(run_id: str) -> None:
    _registry.pop(run_id, None)


def event_visible_for(event: dict[str, Any], *, view: str, seat: int | None) -> bool:
    """Apply the engine visibility model to a serialized event dict.

    god  -> sees everything.
    seat -> sees public events (visible_to is None) plus events whose
            visible_to contains this seat's player id ("player_{seat}").
    """
    if view == "god":
        return True
    visible_to = event.get("visible_to")
    if visible_to is None:
        return True
    if seat is None:
        return False
    return f"player_{seat}" in visible_to


_SPEECH_EVENT_TYPES = frozenset({
    "player_speech",
    "player_discussion",
    "sheriff_candidate_speech",
})


def redact_event_for_seat(event: dict[str, Any], seat: int) -> dict[str, Any]:
    """Strip god-view / LLM-only fields before delivering an event to a seat stream."""
    ev = dict(event)
    et = ev.get("event_type")
    data = dict(ev.get("data") or {})
    self_pid = f"player_{seat}"

    if et in _SPEECH_EVENT_TYPES:
        data.pop("private_thought", None)
        data.pop("reasoning", None)
        if data.get("player_id") != self_pid:
            data.pop("role", None)

    if et in {"actor_thinking", "role_acting"} and data.get("player_id") != self_pid:
        data.pop("role", None)

    ev["data"] = data
    return ev


def read_events_after(run_dir: Path, after_id: int) -> list[dict[str, Any]]:
    """Read events.jsonl lines with event_id > after_id (1-based line numbers).

    Used to replay missed events on (re)connect (Last-Event-ID).
    """
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for idx, raw in enumerate(fh, start=1):
            if idx <= after_id:
                continue
            line = raw.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev["event_id"] = idx
            out.append(ev)
    return out
