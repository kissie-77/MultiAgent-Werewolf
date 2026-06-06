"""Per-run broker that suspends a human seat's decision until the browser submits.

Mirrors ``event_stream.py``: a small in-process registry keyed by ``run_id``.

Flow:
    * :class:`WebHumanAgent` calls :meth:`HumanInputBroker.request` from inside the
      game's asyncio task. ``request`` registers an :class:`asyncio.Future`, pushes an
      ``awaiting_input`` event through the broadcaster (visible only to the human's own
      seat stream + god view), then ``await``\\s the future.
    * The ``POST /games/{id}/input`` route calls :meth:`HumanInputBroker.submit` to
      resolve that future. ``submit`` is idempotent: unknown / already-consumed
      ``request_id`` returns ``False`` and never raises.
    * If no submission arrives before ``deadline`` seconds, ``request`` falls back to a
      safe value and emits ``input_timeout`` so the engine never deadlocks.

``request_id`` is deterministic (``f"{run_id}-{seat}-{counter}"``) — no uuid / random —
so tests can assert on it and so a replayed submit can be matched exactly.
"""

from __future__ import annotations

import asyncio
from typing import Any
from dataclasses import dataclass


@dataclass
class PendingRequest:
    """A single suspended human decision awaiting browser submission."""

    request_id: str
    seat: int
    kind: str
    future: "asyncio.Future[str]"


class HumanInputBroker:
    """Suspend / resume one human seat's decisions for a single run."""

    def __init__(self, run_id: str, seat: int, broadcaster: Any | None = None) -> None:
        self.run_id = run_id
        self.seat = seat
        self._broadcaster = broadcaster
        self._pending: dict[str, PendingRequest] = {}
        self._counter = 0

    # ------------------------------------------------------------------
    # Suspend (called from the game task) / resume (called from HTTP)
    # ------------------------------------------------------------------

    async def request(
        self,
        *,
        kind: str,
        prompt: str,
        valid_targets: list[int],
        fallback: str,
        deadline: float | None = None,
    ) -> str:
        """Register + publish ``awaiting_input`` + await the future.

        Returns the normalized payload text from :meth:`submit`, or ``fallback`` on
        timeout (also emitting ``input_timeout``). Never leaks the pending entry.
        """
        loop = asyncio.get_running_loop()
        rid = f"{self.run_id}-{self.seat}-{self._counter}"
        self._counter += 1
        future: asyncio.Future[str] = loop.create_future()
        self._pending[rid] = PendingRequest(
            request_id=rid, seat=self.seat, kind=kind, future=future
        )
        self._publish(
            {
                "event_type": "awaiting_input",
                "seat": self.seat,
                "request_id": rid,
                "kind": kind,
                "prompt": prompt,
                "valid_targets": list(valid_targets),
                "deadline": deadline,
            }
        )
        try:
            return await asyncio.wait_for(future, deadline)
        except asyncio.TimeoutError:
            self._publish(
                {
                    "event_type": "input_timeout",
                    "seat": self.seat,
                    "request_id": rid,
                    "kind": kind,
                    "fallback": fallback,
                }
            )
            return fallback
        finally:
            self._pending.pop(rid, None)

    def submit(self, *, request_id: str, payload: str) -> bool:
        """Resolve the matching future. Unknown / already-consumed -> ``False``."""
        pending = self._pending.get(request_id)
        if pending is None or pending.future.done():
            return False
        pending.future.set_result(payload)
        self._publish(
            {
                "event_type": "input_received",
                "seat": self.seat,
                "request_id": request_id,
            }
        )
        return True

    def pending_ids(self) -> set[str]:
        return set(self._pending)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _publish(self, event: dict[str, Any]) -> None:
        if self._broadcaster is None:
            return
        # visible_to includes only this seat -> seat stream + god view see it;
        # other seats never learn this player is being asked to act.
        self._broadcaster.publish({**event, "visible_to": [f"player_{self.seat}"]})


_registry: dict[str, HumanInputBroker] = {}


def get_or_create_input_broker(
    run_id: str, seat: int, broadcaster: Any | None = None
) -> HumanInputBroker:
    broker = _registry.get(run_id)
    if broker is None:
        broker = HumanInputBroker(run_id=run_id, seat=seat, broadcaster=broadcaster)
        _registry[run_id] = broker
    return broker


def get_input_broker(run_id: str) -> HumanInputBroker | None:
    return _registry.get(run_id)


def remove_input_broker(run_id: str) -> None:
    _registry.pop(run_id, None)
