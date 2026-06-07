"""Async batch driver: distribute /games/start across backends, poll to terminal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
import asyncio
from dataclasses import dataclass

if TYPE_CHECKING:
    from collections.abc import Callable

    from llm_werewolf.interface.cli.fleet.planner import BatchItem

_TERMINAL = {"completed", "failed", "cancelled"}


@dataclass
class BatchResult:
    seq: int
    backend_url: str
    run_id: str
    status: str
    error: str | None = None


class BatchClient(Protocol):
    async def start_game(self, backend_url: str, config_id: str) -> str: ...

    async def get_status(self, backend_url: str, run_id: str) -> str: ...


class HttpxBatchClient:
    """Default client hitting the real ApiResponse-enveloped endpoints."""

    def __init__(self) -> None:
        import httpx  # noqa: PLC0415 - lazy import keeps httpx optional at module load

        self._httpx = httpx

    async def start_game(self, backend_url: str, config_id: str) -> str:
        async with self._httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{backend_url}/api/v1/games/start", json={"config_id": config_id}
            )
            resp.raise_for_status()
            return resp.json()["data"]["run_id"]

    async def get_status(self, backend_url: str, run_id: str) -> str:
        async with self._httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{backend_url}/api/v1/games/{run_id}/status", params={"source": "runs"}
            )
            resp.raise_for_status()
            return resp.json()["data"]["status"]


async def _start_with_retry(
    cl: BatchClient,
    backend_url: str,
    config_id: str,
    *,
    retries: int,
    backoff_base: float,
    sleep: Callable[[float], Any],
) -> str:
    """Start a game, retrying transient failures (429/timeout/connection) with
    exponential backoff. Raises the last exception once ``retries`` is exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            return await cl.start_game(backend_url, config_id)
        except Exception as exc:
            last_exc = exc
            if attempt + 1 < retries:
                await sleep(backoff_base * (2**attempt))
    raise last_exc if last_exc is not None else RuntimeError("start failed")


async def run_batch(
    items: list[BatchItem],
    *,
    config_id: str,
    concurrency: int,
    client: BatchClient | None = None,
    poll_interval: float = 2.0,
    sleep: Callable[[float], Any] = asyncio.sleep,
    start_retries: int = 3,
    backoff_base: float = 1.0,
) -> list[BatchResult]:
    """Start each item's game (respecting per-item stagger + a concurrency window)
    and poll its status until terminal. Returns one BatchResult per item.

    Failures are isolated per item: a game that cannot be started (after retries)
    or whose polling errors out is recorded as ``status="error"`` instead of
    aborting the whole batch. This keeps a large batch resilient to provider 429s.
    """
    cl = client or HttpxBatchClient()
    sem = asyncio.Semaphore(concurrency)
    results: list[BatchResult | None] = [None] * len(items)

    async def _one(item: BatchItem) -> None:
        async with sem:
            if item.delay_s:
                await sleep(item.delay_s)
            run_id = ""
            try:
                run_id = await _start_with_retry(
                    cl,
                    item.backend_url,
                    config_id,
                    retries=start_retries,
                    backoff_base=backoff_base,
                    sleep=sleep,
                )
                status = "running"
                while status not in _TERMINAL:
                    status = await cl.get_status(item.backend_url, run_id)
                    if status in _TERMINAL:
                        break
                    await sleep(poll_interval)
            except Exception as exc:
                results[item.seq] = BatchResult(
                    seq=item.seq,
                    backend_url=item.backend_url,
                    run_id=run_id,
                    status="error",
                    error=str(exc) or type(exc).__name__,
                )
                return
            results[item.seq] = BatchResult(
                seq=item.seq,
                backend_url=item.backend_url,
                run_id=run_id,
                status=status,
            )

    await asyncio.gather(*(_one(it) for it in items))
    return [r for r in results if r is not None]


def summarize(results: list[BatchResult]) -> dict[str, Any]:
    """Aggregate a batch run for the console / batch_summary.json."""
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "total": len(results),
        "by_status": by_status,
        "runs": [
            {"seq": r.seq, "backend_url": r.backend_url, "run_id": r.run_id, "status": r.status}
            for r in results
        ],
    }
