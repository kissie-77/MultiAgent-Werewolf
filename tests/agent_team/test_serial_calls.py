import asyncio

import pytest

from llm_werewolf.agent_team.serial_calls import run_serial_agent_call
from llm_werewolf.adapter.serial_calls import run_serial_agent_call as compat_call


@pytest.mark.asyncio
async def test_run_serial_agent_call_supports_async_callable() -> None:
    async def call() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert await run_serial_agent_call(call) == "ok"


def test_adapter_serial_calls_is_compatibility_export() -> None:
    assert compat_call is run_serial_agent_call
