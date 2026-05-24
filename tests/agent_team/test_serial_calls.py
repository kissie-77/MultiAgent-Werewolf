import asyncio

import pytest

from llm_werewolf.agent_team.serial_calls import run_serial_agent_call


@pytest.mark.asyncio
async def test_run_serial_agent_call_supports_async_callable() -> None:
    async def call() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert await run_serial_agent_call(call) == "ok"


@pytest.mark.asyncio
async def test_run_serial_agent_call_supports_sync_callable() -> None:
    assert await run_serial_agent_call(lambda: "ok") == "ok"
