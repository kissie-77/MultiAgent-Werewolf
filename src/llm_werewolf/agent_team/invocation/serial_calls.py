"""Shared serial gate for AgentScope model calls.

The default implementation protects providers that rate-limit concurrent
requests. Independent fan-out phases can opt out with a context-local switch
instead of removing the global lock for every call site.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypeVar
import asyncio
import inspect
from contextlib import contextmanager
from contextvars import ContextVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

T = TypeVar("T")

_AGENT_CALL_LOCK = asyncio.Lock()
_SERIALIZE_AGENT_CALLS: ContextVar[bool] = ContextVar("SERIALIZE_AGENT_CALLS", default=True)


def _delay_seconds() -> float:
    raw = os.getenv("AGENT_SERIAL_DELAY_SECONDS", "0")
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0


@contextmanager
def allow_parallel_agent_calls() -> Iterator[None]:
    """Disable the global AgentScope call lock for the current async context."""
    token = _SERIALIZE_AGENT_CALLS.set(False)
    try:
        yield
    finally:
        _SERIALIZE_AGENT_CALLS.reset(token)


async def _execute_agent_call(call: Callable[[], T]) -> T:
    result = call()
    if inspect.isawaitable(result):
        result = await result
    return result


async def run_serial_agent_call(call: Callable[[], T]) -> T:
    """Run one AgentScope call at a time unless the current context opts out."""
    if not _SERIALIZE_AGENT_CALLS.get():
        return await _execute_agent_call(call)

    async with _AGENT_CALL_LOCK:
        result = await _execute_agent_call(call)
        delay = _delay_seconds()
        if delay:
            await asyncio.sleep(delay)
        return result
