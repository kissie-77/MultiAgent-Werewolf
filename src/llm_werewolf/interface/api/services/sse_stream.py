"""Server-Sent Events helpers for GET /games/{run_id}/stream.

Plain StreamingResponse framing (no sse-starlette dependency): each event is
`id: <seq>` / `event: game` / `data: <ViewEvent JSON>`. The JSON payload reuses
build_view._map_event so the stream agrees field-for-field with /view and disk.
A comment-only heartbeat (`: keep-alive`) keeps idle connections open.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from llm_werewolf.interface.api.services.event_hub import _CLOSED
from llm_werewolf.interface.api.services.view import _map_event, _read_jsonl

if TYPE_CHECKING:
    from llm_werewolf.interface.api.services.game_sessions import GameSession

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 15.0


def sse_event_payload(seq: int, row: dict[str, Any]) -> dict[str, Any]:
    """Build the structured ViewEvent dict carried in the SSE `data` field."""
    return _map_event(seq, row).model_dump()


def format_sse(seq: int, event_name: str, data: dict[str, Any]) -> str:
    """Frame one SSE message: id / event / data (JSON), terminated by a blank line."""
    body = json.dumps(data, ensure_ascii=False)
    return f"id: {seq}\nevent: {event_name}\ndata: {body}\n\n"


def format_heartbeat() -> str:
    """Comment-only frame to keep the connection alive through idle phases."""
    return ": keep-alive\n\n"


def backfill_from_disk(run_dir: Path, after_seq: int) -> list[tuple[int, dict[str, Any]]]:
    """Reconstruct (seq, row) pairs from events.jsonl for evicted/finished runs.

    seq is the 0-based line index, matching the hub's 0-based seq and
    build_view's per-event seq (`_map_event(idx, row)`) / cursor (`len(rows)`).
    A fresh connection passes after_seq=-1 to get every row (seq >= 0).
    """
    rows = _read_jsonl(run_dir / "events.jsonl")
    return [(idx, row) for idx, row in enumerate(rows) if idx > after_seq]


async def stream_game(
    *, session: "GameSession | None", run_dir: Path, last_event_id: int
) -> AsyncIterator[str]:
    """Yield SSE frames: backfill (seq > last_event_id) then live, with heartbeats.

    Live session → backfill the missed gap (from events.jsonl FIRST if the
    requested cursor was evicted from the hub's bounded buffer, then from the
    in-buffer seqs), then drain the subscriber queue. On engine error the run
    publishes a terminal type=system error event onto the hub (Task 3 finally
    block) BEFORE closing, so it flows through the live queue / backfill like any
    other event — no special synthesis needed here. Evicted/finished run
    (session is None) → backfill entirely from events.jsonl.
    """
    if session is None:
        for seq, row in backfill_from_disk(run_dir, last_event_id):
            yield format_sse(seq, "game", sse_event_payload(seq, row))
        return

    hub = session.hub
    queue = hub.subscribe()
    try:
        backfilled_through = last_event_id
        # Spec §8: if the requested Last-Event-ID is older than the oldest seq
        # still in the hub's bounded buffer, those seqs were EVICTED. Backfill
        # the missing gap from events.jsonl FIRST, then the in-buffer seqs.
        min_buffered = hub.min_buffered_seq
        if min_buffered is not None and last_event_id < min_buffered - 1:
            # Disk holds seqs [last_event_id+1 .. min_buffered-1] (the gap).
            for seq, row in backfill_from_disk(run_dir, last_event_id):
                if seq >= min_buffered:
                    break  # the rest is still in the hub buffer; avoid duplicates
                yield format_sse(seq, "game", sse_event_payload(seq, row))
                backfilled_through = seq
        # In-buffer backfill: anything missed before the live queue attached.
        for seq, row in hub.backfill(backfilled_through):
            yield format_sse(seq, "game", sse_event_payload(seq, row))
            backfilled_through = seq
        # Live loop with heartbeat on idle.
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield format_heartbeat()
                continue
            if item is _CLOSED:
                break
            seq, row = item
            if seq <= backfilled_through:
                continue  # already sent during backfill
            yield format_sse(seq, "game", sse_event_payload(seq, row))
    finally:
        hub.unsubscribe(queue)
