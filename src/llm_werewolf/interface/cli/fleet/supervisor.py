"""Spawn, health-check, and tear down fleet processes.

I/O lives behind injectable callables so the orchestration logic is unit-testable
without real processes.
"""

from __future__ import annotations

import os
import time
import signal
from typing import TYPE_CHECKING, Protocol
from pathlib import Path
import contextlib
import subprocess

from llm_werewolf.interface.cli.fleet.planner import (
    InstanceSpec,
    build_backend_command,
    build_frontend_command,
)

if TYPE_CHECKING:
    from typing import IO
    from collections.abc import Callable


class ProcHandle(Protocol):
    def terminate(self) -> None: ...

    def is_running(self) -> bool: ...


class _PopenHandle:
    """Default ProcHandle wrapping subprocess.Popen with a redirected log file."""

    def __init__(self, popen: subprocess.Popen, log_file: IO[str] | None) -> None:
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


def _default_spawn(
    name: str, cmd: list[str], env: dict, cwd: str | Path | None, log_path: Path
) -> ProcHandle:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    full_env = {**os.environ, **env}
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    popen = subprocess.Popen(  # noqa: S603 - trusted, internally-built command
        cmd,
        cwd=str(cwd) if cwd else None,
        env=full_env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    return _PopenHandle(popen, log_file)


def _default_health(url: str) -> bool:
    import httpx  # noqa: PLC0415 - lazy import keeps httpx optional at module load

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
        log_dir: str | Path,
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
        for _name, handle in reversed(self._procs):
            with contextlib.suppress(Exception):
                handle.terminate()
        self._procs.clear()

    @property
    def urls(self) -> list[tuple[str, str | None]]:
        return [(s.backend_url, s.frontend_url) for s in self._specs]
