import asyncio

import pytest

from llm_werewolf.agent_team.invocation.serial_calls import run_serial_agent_call


@pytest.mark.asyncio
async def test_run_serial_agent_call_supports_async_callable() -> None:
    async def call() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert await run_serial_agent_call(call) == "ok"


@pytest.mark.asyncio
async def test_run_serial_agent_call_supports_sync_callable() -> None:
    assert await run_serial_agent_call(lambda: "ok") == "ok"


@pytest.mark.asyncio
async def test_run_serial_agent_call_serializes_concurrent_calls_by_default() -> None:
    active = 0
    max_active = 0

    async def call() -> str:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return "ok"

    results = await asyncio.gather(
        run_serial_agent_call(call), run_serial_agent_call(call), run_serial_agent_call(call)
    )

    assert results == ["ok", "ok", "ok"]
    assert max_active == 1


@pytest.mark.asyncio
async def test_allow_parallel_agent_calls_bypasses_lock_in_current_task_context() -> None:
    from llm_werewolf.agent_team.invocation.serial_calls import allow_parallel_agent_calls

    active = 0
    max_active = 0

    async def call() -> str:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return "ok"

    async def unlocked_call() -> str:
        with allow_parallel_agent_calls():
            return await run_serial_agent_call(call)

    results = await asyncio.gather(unlocked_call(), unlocked_call(), unlocked_call())

    assert results == ["ok", "ok", "ok"]
    assert max_active == 3
