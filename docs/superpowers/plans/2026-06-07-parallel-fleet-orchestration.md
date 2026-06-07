# Parallel Fleet Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable launching multiple backend + frontend stacks on distinct ports for parallel game openings (batch eval at scale + multiple human-vs-AI sessions), plus a batch driver that distributes start requests across backends.

**Architecture:** Two backend hardening fixes (collision-proof `run_id`, per-run log handler isolation) make concurrent games safe whether in one process or many. A new `werewolf-fleet` fire CLI plans instances as pure data (`plan_fleet`/`plan_batch`), spawns/health-checks/tears down processes (`ProcessSupervisor`), and runs a distributed batch (`run_batch`). The frontend needs **zero code changes** — instances are parameterized via `VITE_API_PROXY` + `--port`.

**Tech Stack:** Python 3.10+, FastAPI/uvicorn, `fire` (CLI), `httpx` (already installed, 0.28.1), `pytest` + `pytest-asyncio` (asyncio_mode=auto), `contextvars`, `subprocess`. Frontend: Vite (no code change).

**Reference reading before starting:**
- Spec: `docs/superpowers/specs/2026-06-07-parallel-fleet-orchestration-design.md`
- `src/llm_werewolf/interface/api/services/game_sessions.py` (`start_game` lines ~216-220; `_run_game` lines ~294-372)
- `src/llm_werewolf/observability/core/runtime_log.py` (global `_active_handler`)
- `src/llm_werewolf/interface/cli/entry.py` (fire CLI pattern; `fire.Fire`)
- Existing test style: `tests/interface/test_game_sessions_human.py`, `tests/interface/test_start_game_human.py`

**Conventions:**
- Run tests from repo root with: `uv run pytest <path> --no-cov -q` (the global `--cov-fail-under=80` gate fails single-file runs; `--no-cov` avoids the false negative — see project memory).
- Commit messages: Conventional Commits.
- Windows note: this repo runs on win32 via git-bash; use forward slashes and avoid POSIX-only signals in non-test code paths.

---

## File Structure

**Backend changes (hardening):**
- Modify `src/llm_werewolf/interface/api/services/game_sessions.py` — add pure `build_run_id`; wire instance tag + `exist_ok=False`; pass `run_dir` to `detach_run_log_handler`.
- Modify `src/llm_werewolf/observability/core/runtime_log.py` — per-run handler registry + contextvar isolation; keep no-arg `detach` as legacy "detach all".

**New fleet package:**
- Create `src/llm_werewolf/interface/cli/fleet/__init__.py` — re-exports.
- Create `src/llm_werewolf/interface/cli/fleet/planner.py` — `InstanceSpec`, `plan_fleet`, `build_backend_command`, `build_frontend_command`, `BatchItem`, `plan_batch` (all pure).
- Create `src/llm_werewolf/interface/cli/fleet/supervisor.py` — `ProcessSupervisor` (injectable spawn/health for testability) + default Popen/httpx implementations.
- Create `src/llm_werewolf/interface/cli/fleet/batch.py` — `run_batch` async executor + summary aggregation.
- Create `src/llm_werewolf/interface/cli/fleet/entry.py` — fire CLI binding `up` / `batch`.
- Modify `pyproject.toml` — add `werewolf-fleet` to `[project.scripts]`.
- Modify `Makefile` — add `fleet` target.
- Modify `README.md` — add "并行多栈（fleet）" section.

**New tests (all under `tests/interface/`):**
- Create `tests/interface/test_build_run_id.py`
- Create `tests/interface/test_runtime_log_per_run.py`
- Create `tests/interface/test_fleet_planner.py`
- Create `tests/interface/test_fleet_batch_planner.py`
- Create `tests/interface/test_fleet_supervisor.py`
- Create `tests/interface/test_fleet_batch_exec.py`
- Create `tests/interface/test_parallel_sessions.py`
- Create `tests/interface/test_fleet_smoke.py` (opt-in, marked `slow`)

---

## Task 1: Collision-proof `run_id` (keystone)

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Test: `tests/interface/test_build_run_id.py`

- [ ] **Step 1: Write the failing test**

Create `tests/interface/test_build_run_id.py`:

```python
"""Task 1: collision-proof run_id generation."""

from __future__ import annotations

from llm_werewolf.interface.api.services.game_sessions import build_run_id


def test_plain_run_id_no_tag_no_collision() -> None:
    rid = build_run_id("6p-deepseek", "20260607-101500", tag=None, exists=lambda _r: False)
    assert rid == "6p-deepseek-20260607-101500"


def test_tag_is_appended() -> None:
    rid = build_run_id("demo", "20260607-101500", tag="i2", exists=lambda _r: False)
    assert rid == "demo-20260607-101500-i2"


def test_collision_appends_counter() -> None:
    taken = {"demo-20260607-101500"}
    rid = build_run_id("demo", "20260607-101500", tag=None, exists=lambda r: r in taken)
    assert rid == "demo-20260607-101500-2"


def test_collision_counter_increments_until_free() -> None:
    taken = {
        "demo-20260607-101500",
        "demo-20260607-101500-2",
        "demo-20260607-101500-3",
    }
    rid = build_run_id("demo", "20260607-101500", tag=None, exists=lambda r: r in taken)
    assert rid == "demo-20260607-101500-4"


def test_tag_and_collision_compose() -> None:
    taken = {"demo-20260607-101500-i1"}
    rid = build_run_id("demo", "20260607-101500", tag="i1", exists=lambda r: r in taken)
    assert rid == "demo-20260607-101500-i1-2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/interface/test_build_run_id.py --no-cov -q`
Expected: FAIL with `ImportError: cannot import name 'build_run_id'`.

- [ ] **Step 3: Add the pure function**

In `src/llm_werewolf/interface/api/services/game_sessions.py`, add near the top-level helpers (after the imports / before `class GameSessionStatus`), and add `from collections.abc import Callable` is not needed — use `typing`. Insert:

```python
def build_run_id(
    label: str,
    ts: str,
    *,
    tag: str | None,
    exists: "Callable[[str], bool]",
) -> str:
    """Build a unique run_id: ``{label}-{ts}[-{tag}]`` with a collision counter.

    ``exists(run_id)`` reports whether a run dir of that id already exists. The
    counter guarantees uniqueness across same-second opens (single backend) and
    across backends sharing one runs dir (each backend passes a distinct ``tag``).
    """
    base = f"{label}-{ts}"
    if tag:
        base = f"{base}-{tag}"
    if not exists(base):
        return base
    n = 2
    while exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"
```

Add the import at the top of the file (the `typing` block already imports from `typing`):

```python
from typing import TYPE_CHECKING, Any, Callable
```

(Replace the existing `from typing import TYPE_CHECKING, Any` line.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/interface/test_build_run_id.py --no-cov -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/interface/test_build_run_id.py src/llm_werewolf/interface/api/services/game_sessions.py
git commit -m "feat(api): collision-proof build_run_id pure function"
```

---

## Task 2: Wire `build_run_id` + instance tag into `start_game`

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py` (`start_game`, lines ~216-220)
- Test: `tests/interface/test_build_run_id.py` (append a wiring test)

- [ ] **Step 1: Write the failing wiring test**

Append to `tests/interface/test_build_run_id.py`:

```python
from pathlib import Path

from llm_werewolf.interface.api.services.game_sessions import GameSessionManager
from llm_werewolf.interface.api.models.actions import StartGameRequest

_CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs"


async def test_start_game_applies_instance_tag(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WEREWOLF_INSTANCE_TAG", "i7")
    mgr = GameSessionManager()
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    resp = await mgr.start_game(
        configs_dir=_CONFIGS_DIR,
        runs_dir=runs_dir,
        request=StartGameRequest(config_id="demo-6"),
    )
    try:
        assert resp.run_id.endswith("-i7")
        assert (runs_dir / resp.run_id).is_dir()
    finally:
        await mgr.cancel_game(resp.run_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest "tests/interface/test_build_run_id.py::test_start_game_applies_instance_tag" --no-cov -q`
Expected: FAIL (run_id does not end with `-i7` — env tag not read yet).

- [ ] **Step 3: Wire it into `start_game`**

In `src/llm_werewolf/interface/api/services/game_sessions.py`, ensure `import os` is present at the top (add if missing). Replace the run_id block (currently):

```python
        label = (request.run_label or stem).replace("llm-", "")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_id = f"{label}-{ts}"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
```

with:

```python
        label = (request.run_label or stem).replace("llm-", "")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        instance_tag = os.environ.get("WEREWOLF_INSTANCE_TAG") or None
        run_id = build_run_id(
            label, ts, tag=instance_tag, exists=lambda rid: (runs_dir / rid).exists()
        )
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/interface/test_build_run_id.py --no-cov -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/interface/test_build_run_id.py src/llm_werewolf/interface/api/services/game_sessions.py
git commit -m "feat(api): unique run_id per instance tag; mkdir exist_ok=False"
```

---

## Task 3: Per-run log handler isolation

**Files:**
- Modify: `src/llm_werewolf/observability/core/runtime_log.py`
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py` (`_run_game` finally, line ~384)
- Test: `tests/interface/test_runtime_log_per_run.py`

- [ ] **Step 1: Write the failing test**

Create `tests/interface/test_runtime_log_per_run.py`:

```python
"""Task 3: concurrent runs get isolated provider-event log handlers."""

from __future__ import annotations

import json
import logging

from llm_werewolf.observability.core.runtime_log import (
    set_current_run,
    attach_run_log_handler,
    detach_run_log_handler,
)


def _count_lines(path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def test_two_runs_do_not_cross_contaminate(tmp_path) -> None:
    dir_a = tmp_path / "runA"
    dir_b = tmp_path / "runB"
    attach_run_log_handler(dir_a)
    attach_run_log_handler(dir_b)
    logger = logging.getLogger("llm_werewolf.test")
    try:
        set_current_run(str(dir_a))
        logger.warning("provider 429 rate limit hit")
        set_current_run(str(dir_b))
        logger.warning("provider 429 rate limit hit")
    finally:
        set_current_run(None)
        detach_run_log_handler(dir_a)
        detach_run_log_handler(dir_b)

    assert _count_lines(dir_a / "provider_events.jsonl") == 1
    assert _count_lines(dir_b / "provider_events.jsonl") == 1
    payload = json.loads((dir_a / "provider_events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert payload["kind"] == "provider_429"


def test_detach_one_run_leaves_other_active(tmp_path) -> None:
    dir_a = tmp_path / "runA"
    dir_b = tmp_path / "runB"
    attach_run_log_handler(dir_a)
    attach_run_log_handler(dir_b)
    logger = logging.getLogger("llm_werewolf.test")
    try:
        detach_run_log_handler(dir_a)
        set_current_run(str(dir_b))
        logger.warning("provider 429 rate limit hit")
    finally:
        set_current_run(None)
        detach_run_log_handler(dir_b)
    assert _count_lines(dir_a / "provider_events.jsonl") == 0
    assert _count_lines(dir_b / "provider_events.jsonl") == 1


def test_legacy_detach_all_still_works(tmp_path) -> None:
    dir_a = tmp_path / "runA"
    attach_run_log_handler(dir_a)
    logger = logging.getLogger("llm_werewolf.test")
    try:
        logger.warning("provider 429 rate limit hit")  # attach set current run for us
    finally:
        detach_run_log_handler()  # no-arg legacy detach-all
    assert _count_lines(dir_a / "provider_events.jsonl") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/interface/test_runtime_log_per_run.py --no-cov -q`
Expected: FAIL with `ImportError: cannot import name 'set_current_run'`.

- [ ] **Step 3: Rewrite the handler registry in `runtime_log.py`**

In `src/llm_werewolf/observability/core/runtime_log.py`:

Add at the top with the other imports:

```python
import contextvars
```

Replace the global `_active_handler` declaration and the `attach_run_log_handler` / `detach_run_log_handler` functions (lines ~47 and ~85-99) with:

```python
_active_handlers: dict[str, RunObservabilityLogHandler] = {}
_current_run: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ww_current_run", default=None
)


def set_current_run(run_key: str | None) -> None:
    """Tag the current async/sync context with the active run key."""
    _current_run.set(run_key)


def attach_run_log_handler(run_dir: Path) -> str:
    """Bind a per-run handler to the llm_werewolf root logger and mark it current.

    Returns the run key (stringified run_dir). Safe to call concurrently for
    different runs — each handler only emits for records produced within its own
    run context (see ``RunObservabilityLogHandler.emit``).
    """
    key = str(Path(run_dir))
    detach_run_log_handler(run_dir)
    handler = RunObservabilityLogHandler(run_dir)
    logging.getLogger(_ROOT_LOGGER).addHandler(handler)
    _active_handlers[key] = handler
    set_current_run(key)
    return key


def detach_run_log_handler(run_dir: Path | None = None) -> None:
    """Remove the handler for ``run_dir``; with no arg, remove all (legacy)."""
    root = logging.getLogger(_ROOT_LOGGER)
    if run_dir is None:
        for handler in list(_active_handlers.values()):
            root.removeHandler(handler)
        _active_handlers.clear()
        return
    key = str(Path(run_dir))
    handler = _active_handlers.pop(key, None)
    if handler is not None:
        root.removeHandler(handler)
```

Then make the handler context-aware. In `RunObservabilityLogHandler.__init__`, store the key:

```python
    def __init__(self, run_dir: Path) -> None:
        super().__init__(level=logging.WARNING)
        self._run_dir = Path(run_dir)
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._run_dir / "provider_events.jsonl"
        self._run_key = str(self._run_dir)
```

And at the start of `RunObservabilityLogHandler.emit`, before any work:

```python
    def emit(self, record: logging.LogRecord) -> None:
        # Only capture records produced within this run's context. Each game task
        # sets its own context via set_current_run, so concurrent runs don't mix.
        if _current_run.get() != self._run_key:
            return
        try:
            message = record.getMessage()
        ...
```

(The `_current_run` ContextVar is defined below the class, but `emit` runs at call time, so the forward reference resolves fine. If your linter complains, move the `_current_run` / `set_current_run` definitions above the class — both orderings work at runtime.)

- [ ] **Step 4: Update the API caller to detach by run_dir**

In `src/llm_werewolf/interface/api/services/game_sessions.py`, in `_run_game`'s `finally` block, change:

```python
            detach_run_log_handler()
```

to:

```python
            detach_run_log_handler(session.run_dir)
```

(Leave `attach_run_log_handler(session.run_dir)` at the top of `_run_game` as-is — it now also marks the run context.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/interface/test_runtime_log_per_run.py tests/evaluation/signals/test_run_signals.py --no-cov -q`
Expected: PASS (3 new + existing run_signals tests still green — they use no-arg detach which still works).

- [ ] **Step 6: Commit**

```bash
git add tests/interface/test_runtime_log_per_run.py src/llm_werewolf/observability/core/runtime_log.py src/llm_werewolf/interface/api/services/game_sessions.py
git commit -m "fix(obs): per-run provider-event log handlers via contextvar isolation"
```

---

## Task 4: Fleet planner (pure)

**Files:**
- Create: `src/llm_werewolf/interface/cli/fleet/__init__.py`
- Create: `src/llm_werewolf/interface/cli/fleet/planner.py`
- Test: `tests/interface/test_fleet_planner.py`

- [ ] **Step 1: Write the failing test**

Create `tests/interface/test_fleet_planner.py`:

```python
"""Task 4: pure fleet instance planning."""

from __future__ import annotations

import pytest

from llm_werewolf.interface.cli.fleet.planner import (
    plan_fleet,
    build_backend_command,
    build_frontend_command,
)


def test_plan_fleet_ports_and_tags() -> None:
    specs = plan_fleet(backends=4, frontends=4, be_base=8010, fe_base=5173, require_llm=False)
    assert [s.be_port for s in specs] == [8010, 8011, 8012, 8013]
    assert [s.fe_port for s in specs] == [5173, 5174, 5175, 5176]
    assert [s.tag for s in specs] == ["i0", "i1", "i2", "i3"]
    assert specs[2].backend_url == "http://127.0.0.1:8012"
    assert specs[2].frontend_url == "http://127.0.0.1:5175"


def test_backend_env_carries_tag_and_ready_flag() -> None:
    specs = plan_fleet(backends=2, frontends=0, be_base=8010, fe_base=5173, require_llm=False)
    assert specs[1].be_env["WEREWOLF_INSTANCE_TAG"] == "i1"
    assert specs[1].be_env["OBS_READY_REQUIRE_LLM"] == "0"
    assert specs[1].fe_port is None
    assert specs[1].fe_env is None
    assert specs[1].frontend_url is None


def test_frontend_env_points_at_paired_backend() -> None:
    specs = plan_fleet(backends=2, frontends=2, be_base=8010, fe_base=5173, require_llm=True)
    assert specs[1].fe_env["VITE_API_PROXY"] == "http://127.0.0.1:8011"
    assert specs[0].be_env["OBS_READY_REQUIRE_LLM"] == "1"


def test_fewer_frontends_than_backends() -> None:
    specs = plan_fleet(backends=3, frontends=1, be_base=8010, fe_base=5173, require_llm=False)
    assert specs[0].fe_port == 5173
    assert specs[1].fe_port is None
    assert specs[2].fe_port is None


def test_frontends_cannot_exceed_backends() -> None:
    with pytest.raises(ValueError):
        plan_fleet(backends=2, frontends=3, be_base=8010, fe_base=5173, require_llm=False)


def test_backends_must_be_positive() -> None:
    with pytest.raises(ValueError):
        plan_fleet(backends=0, frontends=0, be_base=8010, fe_base=5173, require_llm=False)


def test_build_backend_command_has_port_and_tag_env() -> None:
    specs = plan_fleet(backends=1, frontends=0, be_base=8010, fe_base=5173, require_llm=False)
    cmd = build_backend_command(specs[0])
    assert "werewolf-api" in cmd
    assert "--port" in cmd and "8010" in cmd


def test_build_frontend_command_uses_dev_and_port() -> None:
    specs = plan_fleet(backends=1, frontends=1, be_base=8010, fe_base=5173, require_llm=False)
    cmd = build_frontend_command(specs[0])
    assert "dev" in cmd
    assert "5173" in cmd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/interface/test_fleet_planner.py --no-cov -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'llm_werewolf.interface.cli.fleet'`.

- [ ] **Step 3: Create the package + planner**

Create `src/llm_werewolf/interface/cli/fleet/__init__.py`:

```python
"""Parallel multi-stack (fleet) orchestration: planning, supervision, batch driver."""

from llm_werewolf.interface.cli.fleet.planner import (
    BatchItem,
    InstanceSpec,
    plan_batch,
    plan_fleet,
    build_backend_command,
    build_frontend_command,
)

__all__ = [
    "BatchItem",
    "InstanceSpec",
    "plan_batch",
    "plan_fleet",
    "build_backend_command",
    "build_frontend_command",
]
```

Create `src/llm_werewolf/interface/cli/fleet/planner.py`:

```python
"""Pure planning helpers for fleet orchestration (no I/O, no processes)."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class InstanceSpec:
    """One backend (and optionally one paired frontend) in the fleet."""

    idx: int
    tag: str
    be_port: int
    fe_port: int | None
    be_env: dict[str, str]
    fe_env: dict[str, str] | None
    backend_url: str
    frontend_url: str | None


def plan_fleet(
    *,
    backends: int,
    frontends: int,
    be_base: int,
    fe_base: int,
    require_llm: bool,
) -> list[InstanceSpec]:
    """Plan ``backends`` backend instances and the first ``frontends`` paired frontends.

    Backend i listens on ``be_base + i`` with ``WEREWOLF_INSTANCE_TAG=i{i}``. Frontend i
    (when i < frontends) listens on ``fe_base + i`` and proxies ``/api`` to backend i.
    """
    if backends < 1:
        raise ValueError("backends must be >= 1")
    if frontends < 0 or frontends > backends:
        raise ValueError("frontends must be between 0 and backends")

    specs: list[InstanceSpec] = []
    for idx in range(backends):
        tag = f"i{idx}"
        be_port = be_base + idx
        be_env = {
            "WEREWOLF_INSTANCE_TAG": tag,
            "OBS_READY_REQUIRE_LLM": "1" if require_llm else "0",
        }
        has_fe = idx < frontends
        fe_port = fe_base + idx if has_fe else None
        fe_env = (
            {"VITE_API_PROXY": f"http://127.0.0.1:{be_port}"} if has_fe else None
        )
        specs.append(
            InstanceSpec(
                idx=idx,
                tag=tag,
                be_port=be_port,
                fe_port=fe_port,
                be_env=be_env,
                fe_env=fe_env,
                backend_url=f"http://127.0.0.1:{be_port}",
                frontend_url=f"http://127.0.0.1:{fe_port}" if has_fe else None,
            )
        )
    return specs


def build_backend_command(spec: InstanceSpec) -> list[str]:
    """uvicorn launch command for one backend (current Python interpreter)."""
    return [
        sys.executable,
        "-m",
        "llm_werewolf.interface.api.app",
        "--host",
        "127.0.0.1",
        "--port",
        str(spec.be_port),
    ]


def build_frontend_command(spec: InstanceSpec) -> list[str]:
    """Vite dev launch command for one frontend (run with cwd=frontend)."""
    if spec.fe_port is None:
        raise ValueError(f"instance {spec.idx} has no frontend")
    return ["npm", "run", "dev", "--", "--port", str(spec.fe_port), "--strictPort"]


@dataclass(frozen=True)
class BatchItem:
    """One game to start during a batch run."""

    seq: int
    backend_url: str
    delay_s: float


def plan_batch(
    *,
    count: int,
    backend_urls: list[str],
    stagger: float,
) -> list[BatchItem]:
    """Round-robin ``count`` games across ``backend_urls`` with a per-item start delay.

    Item ``seq`` targets ``backend_urls[seq % n]`` and is delayed ``seq * stagger``
    seconds from t0 (concurrency is enforced separately at execution time).
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    if not backend_urls:
        raise ValueError("backend_urls must be non-empty")
    if stagger < 0:
        raise ValueError("stagger must be >= 0")
    n = len(backend_urls)
    return [
        BatchItem(seq=seq, backend_url=backend_urls[seq % n], delay_s=seq * stagger)
        for seq in range(count)
    ]
```

Note: `app.py:entry` uses `fire.Fire(entry)` via `main()`, so `python -m llm_werewolf.interface.api.app --port N` resolves `--port` through fire. Confirm by reading `app.py` `entry(host, port, reload)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/interface/test_fleet_planner.py --no-cov -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/cli/fleet/__init__.py src/llm_werewolf/interface/cli/fleet/planner.py tests/interface/test_fleet_planner.py
git commit -m "feat(fleet): pure instance + command planning"
```

---

## Task 5: Batch planner tests (pure, completes planner)

**Files:**
- Test: `tests/interface/test_fleet_batch_planner.py`

- [ ] **Step 1: Write the failing test**

Create `tests/interface/test_fleet_batch_planner.py`:

```python
"""Task 5: pure batch distribution planning."""

from __future__ import annotations

import pytest

from llm_werewolf.interface.cli.fleet.planner import plan_batch


def test_round_robin_distribution() -> None:
    items = plan_batch(count=5, backend_urls=["A", "B"], stagger=0.0)
    assert [i.backend_url for i in items] == ["A", "B", "A", "B", "A"]
    assert [i.seq for i in items] == [0, 1, 2, 3, 4]


def test_stagger_delays() -> None:
    items = plan_batch(count=4, backend_urls=["A", "B"], stagger=1.5)
    assert [i.delay_s for i in items] == [0.0, 1.5, 3.0, 4.5]


def test_count_less_than_backends() -> None:
    items = plan_batch(count=1, backend_urls=["A", "B", "C"], stagger=0.0)
    assert len(items) == 1
    assert items[0].backend_url == "A"


def test_validation() -> None:
    with pytest.raises(ValueError):
        plan_batch(count=0, backend_urls=["A"], stagger=0.0)
    with pytest.raises(ValueError):
        plan_batch(count=2, backend_urls=[], stagger=0.0)
    with pytest.raises(ValueError):
        plan_batch(count=2, backend_urls=["A"], stagger=-1.0)
```

- [ ] **Step 2: Run test to verify it passes immediately**

`plan_batch` was already implemented in Task 4. Run: `uv run pytest tests/interface/test_fleet_batch_planner.py --no-cov -q`
Expected: PASS (4 passed). (This task is the dedicated test suite for `plan_batch`; if any assertion fails, fix `plan_batch` in `planner.py` until green.)

- [ ] **Step 3: Commit**

```bash
git add tests/interface/test_fleet_batch_planner.py
git commit -m "test(fleet): batch distribution planning coverage"
```

---

## Task 6: Process supervisor (injectable spawn/health)

**Files:**
- Create: `src/llm_werewolf/interface/cli/fleet/supervisor.py`
- Test: `tests/interface/test_fleet_supervisor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/interface/test_fleet_supervisor.py`:

```python
"""Task 6: ProcessSupervisor orchestration logic with injected fakes."""

from __future__ import annotations

from llm_werewolf.interface.cli.fleet.planner import plan_fleet
from llm_werewolf.interface.cli.fleet.supervisor import ProcessSupervisor, ProcHandle


class FakeProc(ProcHandle):
    def __init__(self, name: str, log: list) -> None:
        self.name = name
        self._log = log
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True
        self._log.append(("terminate", self.name))

    def is_running(self) -> bool:
        return not self.terminated


def test_start_all_spawns_backends_and_frontends() -> None:
    specs = plan_fleet(backends=2, frontends=2, be_base=8010, fe_base=5173, require_llm=False)
    events: list = []

    def fake_spawn(name, cmd, env, cwd, log_path):
        events.append(("spawn", name))
        return FakeProc(name, events)

    sup = ProcessSupervisor(specs, log_dir="/tmp/fleet", spawn=fake_spawn, health=lambda url: True)
    sup.start_all()
    spawned = [n for (kind, n) in events if kind == "spawn"]
    assert spawned == ["backend-i0", "backend-i1", "frontend-i0", "frontend-i1"]


def test_wait_healthy_returns_true_when_all_ok() -> None:
    specs = plan_fleet(backends=2, frontends=0, be_base=8010, fe_base=5173, require_llm=False)
    calls: list = []

    def fake_health(url):
        calls.append(url)
        return True

    sup = ProcessSupervisor(
        specs, log_dir="/tmp/fleet",
        spawn=lambda *a, **k: FakeProc("x", []),
        health=fake_health,
        sleep=lambda _s: None,
    )
    sup.start_all()
    assert sup.wait_healthy(timeout=5.0) is True
    assert "http://127.0.0.1:8010" in calls
    assert "http://127.0.0.1:8011" in calls


def test_wait_healthy_times_out_when_never_ok() -> None:
    specs = plan_fleet(backends=1, frontends=0, be_base=8010, fe_base=5173, require_llm=False)
    ticks = {"t": 0.0}

    def fake_sleep(s):
        ticks["t"] += s

    sup = ProcessSupervisor(
        specs, log_dir="/tmp/fleet",
        spawn=lambda *a, **k: FakeProc("x", []),
        health=lambda url: False,
        sleep=fake_sleep,
        now=lambda: ticks["t"],
    )
    sup.start_all()
    assert sup.wait_healthy(timeout=1.0) is False


def test_teardown_terminates_in_reverse_order() -> None:
    specs = plan_fleet(backends=2, frontends=2, be_base=8010, fe_base=5173, require_llm=False)
    events: list = []
    sup = ProcessSupervisor(
        specs, log_dir="/tmp/fleet",
        spawn=lambda name, *a, **k: FakeProc(name, events),
        health=lambda url: True,
    )
    sup.start_all()
    sup.teardown()
    terminated = [n for (kind, n) in events if kind == "terminate"]
    assert terminated == ["frontend-i1", "frontend-i0", "backend-i1", "backend-i0"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/interface/test_fleet_supervisor.py --no-cov -q`
Expected: FAIL with `ImportError: cannot import name 'ProcessSupervisor'`.

- [ ] **Step 3: Implement the supervisor**

Create `src/llm_werewolf/interface/cli/fleet/supervisor.py`:

```python
"""Spawn, health-check, and tear down fleet processes. I/O lives behind injectable
callables so the orchestration logic is unit-testable without real processes."""

from __future__ import annotations

import os
import sys
import time
import signal
import subprocess
from typing import Callable, Protocol
from pathlib import Path

from llm_werewolf.interface.cli.fleet.planner import (
    InstanceSpec,
    build_backend_command,
    build_frontend_command,
)


class ProcHandle(Protocol):
    def terminate(self) -> None: ...
    def is_running(self) -> bool: ...


class _PopenHandle:
    """Default ProcHandle wrapping subprocess.Popen with a redirected log file."""

    def __init__(self, popen: subprocess.Popen, log_file) -> None:
        self._popen = popen
        self._log_file = log_file

    def terminate(self) -> None:
        if self._popen.poll() is None:
            if os.name == "nt":
                self._popen.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            else:
                self._popen.terminate()
            try:
                self._popen.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._popen.kill()
        if self._log_file is not None:
            self._log_file.close()

    def is_running(self) -> bool:
        return self._popen.poll() is None


def _default_spawn(name: str, cmd: list[str], env: dict, cwd, log_path: Path) -> ProcHandle:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    full_env = {**os.environ, **env}
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    popen = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=full_env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    return _PopenHandle(popen, log_file)


def _default_health(url: str) -> bool:
    import httpx

    try:
        resp = httpx.get(f"{url}/health", timeout=2.0)
        return resp.status_code == 200 and resp.json().get("status") == "ok"
    except Exception:
        return False


class ProcessSupervisor:
    """Start backends then frontends, poll health, and tear all down in reverse."""

    def __init__(
        self,
        specs: list[InstanceSpec],
        *,
        log_dir,
        spawn: Callable[..., ProcHandle] = _default_spawn,
        health: Callable[[str], bool] = _default_health,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
        frontend_cwd: Path | None = None,
    ) -> None:
        self._specs = specs
        self._log_dir = Path(log_dir)
        self._spawn = spawn
        self._health = health
        self._sleep = sleep
        self._now = now
        self._frontend_cwd = frontend_cwd or (Path.cwd() / "frontend")
        # ordered list of (name, handle); teardown reverses it
        self._procs: list[tuple[str, ProcHandle]] = []

    def start_all(self) -> None:
        for spec in self._specs:
            name = f"backend-{spec.tag}"
            handle = self._spawn(
                name,
                build_backend_command(spec),
                spec.be_env,
                None,
                self._log_dir / f"{name}.log",
            )
            self._procs.append((name, handle))
        for spec in self._specs:
            if spec.fe_port is None:
                continue
            name = f"frontend-{spec.tag}"
            handle = self._spawn(
                name,
                build_frontend_command(spec),
                spec.fe_env or {},
                self._frontend_cwd,
                self._log_dir / f"{name}.log",
            )
            self._procs.append((name, handle))

    def wait_healthy(self, *, timeout: float, poll: float = 0.5) -> bool:
        deadline = self._now() + timeout
        pending = [s.backend_url for s in self._specs]
        while pending and self._now() < deadline:
            pending = [url for url in pending if not self._health(url)]
            if not pending:
                return True
            self._sleep(poll)
        return not pending

    def teardown(self) -> None:
        for name, handle in reversed(self._procs):
            try:
                handle.terminate()
            except Exception:
                pass
        self._procs.clear()

    @property
    def urls(self) -> list[tuple[str, str | None]]:
        return [(s.backend_url, s.frontend_url) for s in self._specs]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/interface/test_fleet_supervisor.py --no-cov -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/cli/fleet/supervisor.py tests/interface/test_fleet_supervisor.py
git commit -m "feat(fleet): ProcessSupervisor with injectable spawn/health"
```

---

## Task 7: Batch executor (async, injectable client)

**Files:**
- Create: `src/llm_werewolf/interface/cli/fleet/batch.py`
- Test: `tests/interface/test_fleet_batch_exec.py`

- [ ] **Step 1: Write the failing test**

Create `tests/interface/test_fleet_batch_exec.py`:

```python
"""Task 7: batch executor distributes starts and polls to terminal states."""

from __future__ import annotations

from llm_werewolf.interface.cli.fleet.planner import plan_batch
from llm_werewolf.interface.cli.fleet.batch import run_batch, BatchResult


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


async def _noop() -> None:
    return None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/interface/test_fleet_batch_exec.py --no-cov -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'llm_werewolf.interface.cli.fleet.batch'`.

- [ ] **Step 3: Implement the batch executor**

Create `src/llm_werewolf/interface/cli/fleet/batch.py`:

```python
"""Async batch driver: distribute /games/start across backends, poll to terminal."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Protocol
from dataclasses import dataclass

from llm_werewolf.interface.cli.fleet.planner import BatchItem

_TERMINAL = {"completed", "failed", "cancelled"}


@dataclass
class BatchResult:
    seq: int
    backend_url: str
    run_id: str
    status: str


class BatchClient(Protocol):
    async def start_game(self, backend_url: str, config_id: str) -> str: ...
    async def get_status(self, backend_url: str, run_id: str) -> str: ...


class HttpxBatchClient:
    """Default client hitting the real ApiResponse-enveloped endpoints."""

    def __init__(self) -> None:
        import httpx

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


async def run_batch(
    items: list[BatchItem],
    *,
    config_id: str,
    concurrency: int,
    client: BatchClient | None = None,
    poll_interval: float = 2.0,
    sleep: Callable[[float], Any] = asyncio.sleep,
) -> list[BatchResult]:
    """Start each item's game (respecting per-item stagger + a concurrency window)
    and poll its status until terminal. Returns one BatchResult per item."""
    cl = client or HttpxBatchClient()
    sem = asyncio.Semaphore(concurrency)
    results: list[BatchResult | None] = [None] * len(items)

    async def _one(item: BatchItem) -> None:
        async with sem:
            if item.delay_s:
                await sleep(item.delay_s)
            run_id = await cl.start_game(item.backend_url, config_id)
            status = "running"
            while status not in _TERMINAL:
                status = await cl.get_status(item.backend_url, run_id)
                if status in _TERMINAL:
                    break
                await sleep(poll_interval)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/interface/test_fleet_batch_exec.py --no-cov -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Add a summarize test**

Append to `tests/interface/test_fleet_batch_exec.py`:

```python
from llm_werewolf.interface.cli.fleet.batch import summarize


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
```

Run: `uv run pytest tests/interface/test_fleet_batch_exec.py --no-cov -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/llm_werewolf/interface/cli/fleet/batch.py tests/interface/test_fleet_batch_exec.py
git commit -m "feat(fleet): async batch driver with concurrency + stagger"
```

---

## Task 8: Fleet CLI entry (`up` / `batch`) + packaging

**Files:**
- Create: `src/llm_werewolf/interface/cli/fleet/entry.py`
- Modify: `pyproject.toml` (`[project.scripts]`)
- Modify: `Makefile`
- Test: `tests/interface/test_fleet_supervisor.py` (append CLI-layer assembly test)

- [ ] **Step 1: Write the failing test for the run-dir stamp helper**

Append to `tests/interface/test_fleet_supervisor.py`:

```python
from llm_werewolf.interface.cli.fleet.entry import build_log_dir


def test_build_log_dir_under_artifacts_fleet(tmp_path) -> None:
    out = build_log_dir(root=tmp_path, stamp="20260607-101500")
    assert out == tmp_path / "artifacts" / "fleet" / "20260607-101500"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest "tests/interface/test_fleet_supervisor.py::test_build_log_dir_under_artifacts_fleet" --no-cov -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'llm_werewolf.interface.cli.fleet.entry'`.

- [ ] **Step 3: Implement the CLI entry**

Create `src/llm_werewolf/interface/cli/fleet/entry.py`:

```python
"""`werewolf-fleet` CLI: `up` launches a multi-stack fleet; `batch` distributes games."""

from __future__ import annotations

import sys
import json
import time
import asyncio
import contextlib
from pathlib import Path
from datetime import datetime

import fire

from llm_werewolf.interface.cli.fleet.batch import run_batch, summarize
from llm_werewolf.interface.cli.fleet.planner import plan_batch, plan_fleet
from llm_werewolf.interface.cli.fleet.supervisor import ProcessSupervisor


def build_log_dir(*, root: Path, stamp: str) -> Path:
    return Path(root) / "artifacts" / "fleet" / stamp


def _print_table(specs) -> None:
    print("\n  idx | backend                  | frontend")
    print("  ----+--------------------------+-------------------------")
    for s in specs:
        fe = s.frontend_url or "(none)"
        print(f"  {s.idx:>3} | {s.backend_url:<24} | {fe}")
    print()


def up(
    backends: int = 2,
    frontends: int | None = None,
    be_base: int = 8010,
    fe_base: int = 5173,
    require_llm: bool = False,
    health_timeout: float = 60.0,
) -> None:
    """Launch ``backends`` backends + ``frontends`` frontends (default: == backends)."""
    if frontends is None:
        frontends = backends
    specs = plan_fleet(
        backends=backends,
        frontends=frontends,
        be_base=be_base,
        fe_base=fe_base,
        require_llm=require_llm,
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = build_log_dir(root=Path.cwd(), stamp=stamp)
    sup = ProcessSupervisor(specs, log_dir=log_dir)
    print(f"[fleet] starting {backends} backend(s), {frontends} frontend(s); logs -> {log_dir}")
    sup.start_all()
    try:
        if sup.wait_healthy(timeout=health_timeout):
            print("[fleet] all backends healthy.")
        else:
            print("[fleet] WARNING: some backends did not become healthy; see logs.")
        _print_table(specs)
        print("[fleet] Ctrl-C to stop all processes.")
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[fleet] shutting down...")
    finally:
        sup.teardown()
        print("[fleet] all processes terminated.")


def batch(
    config: str = "demo-6",
    count: int = 4,
    be_base: int = 8010,
    backends: int = 2,
    concurrency: int = 2,
    stagger: float = 1.0,
) -> None:
    """Distribute ``count`` games across already-running backends and poll to terminal.

    Targets backends at ``be_base + i`` for i in range(``backends``). Start a fleet first
    with ``werewolf-fleet up --backends N`` (or point at any running backends).
    """
    backend_urls = [f"http://127.0.0.1:{be_base + i}" for i in range(backends)]
    items = plan_batch(count=count, backend_urls=backend_urls, stagger=stagger)
    print(f"[batch] {count} games across {backends} backend(s), concurrency={concurrency}")
    results = asyncio.run(run_batch(items, config_id=config, concurrency=concurrency))
    summary = summarize(results)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = build_log_dir(root=Path.cwd(), stamp=stamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "batch_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[batch] done: {summary['by_status']}  ->  {out}")


def entry() -> None:
    # Windows: keep zh/emoji output UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fire.Fire({"up": up, "batch": batch})


if __name__ == "__main__":
    entry()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/interface/test_fleet_supervisor.py --no-cov -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Register the console script**

In `pyproject.toml`, under `[project.scripts]` (after `werewolf-api = ...`), add:

```toml
werewolf-fleet = "llm_werewolf.interface.cli.fleet.entry:entry"
```

Re-sync so the entry point is installed: `uv sync --group dev --group test`

- [ ] **Step 6: Verify the CLI is wired (help text)**

Run: `uv run werewolf-fleet up --help`
Expected: fire shows the `up` signature (backends, frontends, be_base, ...). No traceback.

- [ ] **Step 7: Add Makefile target**

In `Makefile`, after the `dev-web` target, add:

```makefile
.PHONY: fleet
fleet:
	$(RUN) werewolf-fleet up --backends 2
```

- [ ] **Step 8: Commit**

```bash
git add src/llm_werewolf/interface/cli/fleet/entry.py pyproject.toml Makefile tests/interface/test_fleet_supervisor.py
git commit -m "feat(fleet): werewolf-fleet up/batch CLI + packaging"
```

---

## Task 9: Backend integration test — concurrent opens don't collide

**Files:**
- Test: `tests/interface/test_parallel_sessions.py`

- [ ] **Step 1: Write the test**

Create `tests/interface/test_parallel_sessions.py`:

```python
"""Concurrent game opens get isolated run_ids, dirs, and event logs."""

from __future__ import annotations

import asyncio
from pathlib import Path

from llm_werewolf.interface.api.services.game_sessions import GameSessionManager
from llm_werewolf.interface.api.services.game_sessions import GameSessionStatus
from llm_werewolf.interface.api.models.actions import StartGameRequest

_CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs"


async def test_two_concurrent_demo_games_are_isolated(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    mgr = GameSessionManager()
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    req = StartGameRequest(config_id="demo-6")
    r1, r2 = await asyncio.gather(
        mgr.start_game(configs_dir=_CONFIGS_DIR, runs_dir=runs_dir, request=req),
        mgr.start_game(configs_dir=_CONFIGS_DIR, runs_dir=runs_dir, request=req),
    )
    try:
        # Distinct run ids and distinct directories.
        assert r1.run_id != r2.run_id
        assert (runs_dir / r1.run_id).is_dir()
        assert (runs_dir / r2.run_id).is_dir()
        # Both sessions live in the registry simultaneously.
        assert r1.run_id in mgr._sessions
        assert r2.run_id in mgr._sessions
        # Let both play to completion (demo games are fast, no LLM key needed).
        await asyncio.wait_for(
            asyncio.gather(
                mgr._sessions[r1.run_id].task,
                mgr._sessions[r2.run_id].task,
            ),
            timeout=120,
        )
        # Each wrote its own events.jsonl independently.
        e1 = (runs_dir / r1.run_id / "events.jsonl")
        e2 = (runs_dir / r2.run_id / "events.jsonl")
        assert e1.is_file() and e2.is_file()
        assert mgr._sessions[r1.run_id].status == GameSessionStatus.COMPLETED
        assert mgr._sessions[r2.run_id].status == GameSessionStatus.COMPLETED
    finally:
        for rid in (r1.run_id, r2.run_id):
            sess = mgr._sessions.get(rid)
            if sess and sess.task and not sess.task.done():
                await mgr.cancel_game(rid)
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/interface/test_parallel_sessions.py --no-cov -q`
Expected: PASS (1 passed). If it times out, demo-6 may need longer — bump the timeout, but it should finish in well under 120s with no LLM calls.

- [ ] **Step 3: Commit**

```bash
git add tests/interface/test_parallel_sessions.py
git commit -m "test(api): two concurrent demo games stay isolated"
```

---

## Task 10: Opt-in smoke test + docs

**Files:**
- Create: `tests/interface/test_fleet_smoke.py`
- Modify: `README.md`

- [ ] **Step 1: Write the opt-in smoke test**

Create `tests/interface/test_fleet_smoke.py`:

```python
"""Opt-in smoke test: spin up 2 real demo backends, health-check, tear down.

Skipped by default (real subprocesses + ports). Run explicitly:
    uv run pytest tests/interface/test_fleet_smoke.py --no-cov -q -m fleet_smoke -o addopts=""
"""

from __future__ import annotations

import socket

import pytest

from llm_werewolf.interface.cli.fleet.planner import plan_fleet
from llm_werewolf.interface.cli.fleet.supervisor import ProcessSupervisor

pytestmark = pytest.mark.fleet_smoke


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_two_backends_become_healthy_and_teardown(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    be_base = _free_port()
    specs = plan_fleet(
        backends=2, frontends=0, be_base=be_base, fe_base=5173, require_llm=False
    )
    sup = ProcessSupervisor(specs, log_dir=tmp_path / "artifacts" / "fleet" / "smoke")
    sup.start_all()
    try:
        assert sup.wait_healthy(timeout=60.0) is True
    finally:
        sup.teardown()
```

Note: `be_base` from `_free_port()` plus 1 (for the 2nd backend) may collide rarely; acceptable for an opt-in smoke test. Register the marker in `pyproject.toml` under `[tool.pytest.ini_options] markers` (add `"fleet_smoke: opt-in fleet smoke tests (real subprocesses)"`) to silence the unknown-marker warning.

- [ ] **Step 2: Verify it is skipped by default**

Run: `uv run pytest tests/interface/test_fleet_smoke.py --no-cov -q`
Expected: the test is collected but NOT run by default only if a `-m "not fleet_smoke"` default exists; otherwise it WILL run. To keep CI fast without changing global addopts, leave it runnable but document the explicit opt-in command. Run it once manually to confirm it passes:
Run: `uv run pytest tests/interface/test_fleet_smoke.py --no-cov -q`
Expected: PASS (1 passed) — 2 uvicorn demo backends start, report healthy, and are torn down.

- [ ] **Step 3: Document in README**

In `README.md`, after the "本地全栈开发（前端 + 后端）" section, add:

````markdown
## 并行多栈（fleet）：同时开多局

一条命令拉起 N 套（后端 + 前端）各自独立端口，用于并行开局（批量评测 / 多个真人各自一局）。

```bash
# 拉起 2 套后端(8010/8011) + 2 套前端(5173/5174)；Ctrl-C 全部停止
DEEPSEEK_API_KEY=sk-xxx uv run werewolf-fleet up --backends 2

# 仅后端（评测用，不起 vite）
uv run werewolf-fleet up --backends 4 --frontends 0

# 批量开局：把 20 局分发到 4 个后端，并发 4、相邻启动错峰 1.5s（抗 429）
uv run werewolf-fleet batch --config llm-6p-deepseek --count 20 --backends 4 --concurrency 4 --stagger 1.5
```

- 每个后端进程拿到 `WEREWOLF_INSTANCE_TAG=iN`，`run_id` 形如 `6p-deepseek-<ts>-iN`，多后端共享 `artifacts/runs/` 不会撞车。
- 每个前端通过 `VITE_API_PROXY` 指向自己的后端；人机对战把 `http://localhost:<fe_port>/` 分给各真人即可。
- 日志：`artifacts/fleet/<stamp>/backend-iN.log` / `frontend-iN.log`；批量汇总 `artifacts/fleet/<stamp>/batch_summary.json`。
- **限流提示**：所有后端共用同一个 LLM key，规模大时用 `--concurrency` / `--stagger` 错峰，避免 429。
````

- [ ] **Step 4: Commit**

```bash
git add tests/interface/test_fleet_smoke.py pyproject.toml README.md
git commit -m "test(fleet): opt-in smoke test; docs for parallel multi-stack"
```

---

## Task 11: Full regression + manual E2E checklist

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite (with coverage gate, as CI does)**

Run: `uv run pytest tests/interface --no-cov -q`
Expected: all interface tests pass (existing + new). Then run the full suite once:
Run: `uv run pytest -q` (or `make test-fast`)
Expected: green (no regressions in game_sessions / runtime_log / run_signals).

- [ ] **Step 2: Lint**

Run: `uv run ruff check src/llm_werewolf/interface/cli/fleet src/llm_werewolf/observability/core/runtime_log.py src/llm_werewolf/interface/api/services/game_sessions.py`
Expected: no errors (fix any import-order / unused per ruff).

- [ ] **Step 3: Manual fleet smoke (demo, no key)**

Run in a terminal: `uv run werewolf-fleet up --backends 2 --frontends 0`
Expected: prints a table with `http://127.0.0.1:8010` and `:8011`, "all backends healthy". In another terminal:
`curl http://127.0.0.1:8010/health` and `curl http://127.0.0.1:8011/health` → both `{"status":"ok"}`.
Ctrl-C the fleet → "all processes terminated"; confirm no orphan python/uvicorn left (`tasklist | grep -i python` on Windows / `ps` on POSIX).

- [ ] **Step 4: Manual batch (demo, no key)**

With the 2-backend fleet still up, run:
`uv run werewolf-fleet batch --config demo-6 --count 4 --backends 2 --concurrency 2 --stagger 0.5`
Expected: `[batch] done: {'completed': 4}` and a `batch_summary.json` with 4 runs split across `:8010`/`:8011`. Confirm 4 distinct run dirs under `artifacts/runs/` with `-i0` / `-i1` tags.

- [ ] **Step 5: Manual real-machine E2E (with LLM key + frontends) — optional**

`DEEPSEEK_API_KEY=sk-xxx uv run werewolf-fleet up --backends 2 --frontends 2` then open `http://localhost:5173` and `http://localhost:5174` in two browser tabs, start a game in each, and confirm via Playwright/manual that the two SSE streams are independent and seat tokens don't cross (per the existing M3 E2E approach in project memory).

- [ ] **Step 6: Update project memory**

Append the fleet feature to `C:\Users\18092\.claude\projects\D--AI-werewolf-werewolf-6-6-MultiAgent-Werewolf\memory\fe-be-integration.md` (run_id uniqueness fix + per-run log handler + `werewolf-fleet up/batch`), so future sessions know it exists.

---

## Self-Review

**Spec coverage:**
- §2 run_id collision (keystone) → Tasks 1, 2, 9. ✅
- §3 R1 (run_id) → Tasks 1,2; R3 (rate limit: concurrency+stagger) → Task 7,8 (`--concurrency`/`--stagger`); R4 (frontends optional) → `--frontends 0` Task 8; R6 (log handler) → Task 3; R7 (teardown / Windows process group) → Task 6 (`CREATE_NEW_PROCESS_GROUP`, reverse teardown). ✅
- §4.2(a) build_run_id + exist_ok=False → Tasks 1,2. ✅
- §4.2(b) per-run handler → Task 3. ✅
- §4.3 FleetPlanner/BatchPlanner/ProcessSupervisor/entry/batch + pyproject → Tasks 4,5,6,7,8. ✅
- §4.4 frontend zero-change (env only) → covered by planner env + docs; no FE task. ✅
- §4.5 Makefile + README → Tasks 8,10. ✅
- §5 tests: pure (1-7), integration (9), smoke (10), manual E2E (11). ✅
- §6 non-goals (`--isolate-runs`, per-instance key, compose, log rotation, multi-game UI) → intentionally omitted. ✅

**Placeholder scan:** No TBD/TODO; every code step has full code. ✅

**Type consistency:** `InstanceSpec` fields (idx, tag, be_port, fe_port, be_env, fe_env, backend_url, frontend_url) used consistently in planner/supervisor/entry. `BatchItem`(seq, backend_url, delay_s) and `BatchResult`(seq, backend_url, run_id, status) consistent across batch.py + tests. `ProcessSupervisor(specs, *, log_dir, spawn, health, sleep, now, frontend_cwd)` matches all test call sites. `build_run_id(label, ts, *, tag, exists)` matches all call sites. `detach_run_log_handler(run_dir=None)` matches caller updates. ✅
