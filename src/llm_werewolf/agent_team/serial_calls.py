"""Shared serial gate for AgentScope model calls.

The default implementation is intentionally small: it protects providers that
rate-limit concurrent requests while keeping the call site independent from any
local-only helper file.
"""

from __future__ import annotations

import asyncio
import inspect
import os
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_AGENT_CALL_LOCK = asyncio.Lock()


def _delay_seconds() -> float:
    raw = os.getenv("AGENT_SERIAL_DELAY_SECONDS", "0")
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0


async def run_serial_agent_call(call: Callable[[], T]) -> T:
    """Run one AgentScope call at a time, with optional post-call delay."""
    async with _AGENT_CALL_LOCK:
        result = call()
        if inspect.isawaitable(result):
            result = await result
        delay = _delay_seconds()
        if delay:
            await asyncio.sleep(delay)
        return result
