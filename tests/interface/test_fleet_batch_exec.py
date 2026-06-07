"""Task 7: batch executor distributes starts and polls to terminal states."""

from __future__ import annotations

from llm_werewolf.interface.cli.fleet.batch import BatchResult, run_batch, summarize
from llm_werewolf.interface.cli.fleet.planner import plan_batch


class FakeClient:
    """Stub of the minimal async HTTP surface run_batch uses."""

    def __init__(self) -> None:
        self.started: list[tuple[str, str]] = []  # (backend_url, config_id)
        self._poll_counts: dict[str, int] = {}

    async def start_game(self, backend_url: str, config_id: str) -> str:
        self.started.append((backend_url, config_id))
        run_id = f"{config_id}-{len(self.started)}"
        self._poll_counts[run_id] = 0
        return run_id

    async def get_status(self, backend_url: str, run_id: str) -> str:
        self._poll_counts[run_id] += 1
        # running for the first poll, then completed
        return "running" if self._poll_counts[run_id] < 2 else "completed"


async def _noop() -> None:
    return None


async def test_run_batch_distributes_and_completes() -> None:
    items = plan_batch(count=4, backend_urls=["A", "B"], stagger=0.0)
    client = FakeClient()
    results = await run_batch(
        items,
        config_id="demo-6",
        concurrency=2,
        client=client,
        poll_interval=0.0,
        sleep=lambda _s: _noop(),
    )
    # round-robin: A,B,A,B
    assert [b for (b, _c) in client.started] == ["A", "B", "A", "B"]
    assert len(results) == 4
    assert all(isinstance(r, BatchResult) for r in results)
    assert all(r.status == "completed" for r in results)
    assert {r.backend_url for r in results} == {"A", "B"}


def test_summarize_counts_by_status() -> None:
    results = [
        BatchResult(seq=0, backend_url="A", run_id="r0", status="completed"),
        BatchResult(seq=1, backend_url="B", run_id="r1", status="completed"),
        BatchResult(seq=2, backend_url="A", run_id="r2", status="failed"),
    ]
    s = summarize(results)
    assert s["total"] == 3
    assert s["by_status"] == {"completed": 2, "failed": 1}
    assert len(s["runs"]) == 3


class FlakyStartClient:
    """A client whose ``start_game`` always raises for a given set of backends."""

    def __init__(self, fail_backends: set[str]) -> None:
        self.started: list[tuple[str, str]] = []
        self._poll_counts: dict[str, int] = {}
        self._fail_backends = fail_backends

    async def start_game(self, backend_url: str, config_id: str) -> str:
        if backend_url in self._fail_backends:
            raise RuntimeError(f"start failed on {backend_url}")
        self.started.append((backend_url, config_id))
        run_id = f"{config_id}-{len(self.started)}"
        self._poll_counts[run_id] = 0
        return run_id

    async def get_status(self, backend_url: str, run_id: str) -> str:
        self._poll_counts[run_id] += 1
        return "completed"


async def test_run_batch_isolates_failures_and_keeps_going() -> None:
    # Round-robin A,B,A,B; backend B always fails to start.
    items = plan_batch(count=4, backend_urls=["A", "B"], stagger=0.0)
    client = FlakyStartClient(fail_backends={"B"})
    results = await run_batch(
        items,
        config_id="demo-6",
        concurrency=2,
        client=client,
        poll_interval=0.0,
        sleep=lambda _s: _noop(),
        start_retries=1,
    )
    by_seq = {r.seq: r for r in results}
    assert len(results) == 4  # the whole batch survives B's failures
    assert by_seq[0].status == "completed"  # A
    assert by_seq[2].status == "completed"  # A
    assert by_seq[1].status == "error"  # B
    assert by_seq[3].status == "error"  # B
    assert by_seq[1].error  # carries a message
    # A summary still aggregates cleanly.
    assert summarize(results)["by_status"] == {"completed": 2, "error": 2}


class TransientStartClient:
    """``start_game`` fails the first ``fail_first`` attempts, then succeeds."""

    def __init__(self, fail_first: int) -> None:
        self.attempts = 0
        self.started: list[str] = []
        self._poll_counts: dict[str, int] = {}
        self._fail_first = fail_first

    async def start_game(self, backend_url: str, config_id: str) -> str:
        self.attempts += 1
        if self.attempts <= self._fail_first:
            raise RuntimeError("transient 429")
        self.started.append(backend_url)
        run_id = f"{config_id}-{len(self.started)}"
        self._poll_counts[run_id] = 0
        return run_id

    async def get_status(self, backend_url: str, run_id: str) -> str:
        self._poll_counts[run_id] += 1
        return "completed"


async def test_run_batch_retries_transient_start_failure() -> None:
    items = plan_batch(count=1, backend_urls=["A"], stagger=0.0)
    client = TransientStartClient(fail_first=1)
    slept: list[float] = []

    async def fake_sleep(s: float) -> None:
        slept.append(s)

    results = await run_batch(
        items,
        config_id="x",
        concurrency=1,
        client=client,
        poll_interval=0.0,
        sleep=fake_sleep,
        start_retries=3,
        backoff_base=0.5,
    )
    assert len(results) == 1
    assert results[0].status == "completed"
    assert client.attempts == 2  # failed once, retried once, then succeeded
    assert any(s > 0 for s in slept)  # a backoff delay was applied
