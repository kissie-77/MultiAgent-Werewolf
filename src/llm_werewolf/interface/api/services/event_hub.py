"""In-process publish/subscribe hub for live engine events.

One source (engine.on_event) fans out to two sinks: the disk writer
(events.jsonl, unchanged) and this hub. The hub assigns a monotonic
``seq`` to every event, keeps a bounded ring buffer so reconnecting SSE
clients can backfill ``seq > Last-Event-ID``, and pushes each event to a
bounded per-subscriber queue.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel pushed to every subscriber queue when the stream is closed.
_CLOSED = object()


class EventHub:
    """Per-run in-memory event bus with seq numbering and backfill."""

    def __init__(self, buffer_size: int = 4096, queue_size: int = 1024) -> None:
        self._buffer: deque[tuple[int, dict[str, Any]]] = deque(maxlen=buffer_size)
        self._subscribers: list[asyncio.Queue[Any]] = []
        # 0-based: the seq to assign to the NEXT published event. After N
        # publishes this equals N, matching build_view's cursor=len(rows).
        self._next_seq = 0
        self._queue_size = queue_size
        self._closed = False

    @property
    def next_seq(self) -> int:
        """The seq the next published event will get (== count published == /view cursor)."""
        return self._next_seq

    @property
    def min_buffered_seq(self) -> int | None:
        """Smallest seq still in the ring buffer, or None when empty.

        Used by the stream route to detect that a requested Last-Event-ID is
        older than the buffer (evicted) so it must backfill from events.jsonl.
        """
        return self._buffer[0][0] if self._buffer else None

    def publish(self, row: dict[str, Any]) -> int:
        """Assign the next 0-based seq, buffer the row, fan it out. Returns the seq."""
        seq = self._next_seq
        self._next_seq += 1
        item = (seq, row)
        self._buffer.append(item)
        for queue in self._subscribers:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                logger.warning("EventHub subscriber queue full; dropping seq=%s", seq)
        return seq

    def backfill(self, after_seq: int) -> list[tuple[int, dict[str, Any]]]:
        """Return buffered (seq, row) with seq > after_seq, in seq order.

        A fresh connection passes after_seq=-1 to get every buffered event
        (seq >= 0); Last-Event-ID=N passes after_seq=N to resume after seq N.
        """
        return [item for item in self._buffer if item[0] > after_seq]

    def subscribe(self) -> asyncio.Queue[Any]:
        """Register a new live subscriber queue."""
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.append(queue)
        if self._closed:
            queue.put_nowait(_CLOSED)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Any]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def close(self) -> None:
        """Signal end-of-stream to all current subscribers."""
        self._closed = True
        for queue in self._subscribers:
            try:
                queue.put_nowait(_CLOSED)
            except asyncio.QueueFull:
                pass

    @property
    def closed(self) -> bool:
        return self._closed
