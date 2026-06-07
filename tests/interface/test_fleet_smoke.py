"""Opt-in smoke test: spin up 2 real demo backends, health-check, tear down.

Skipped by default (real subprocesses + ports). Run explicitly:
    RUN_FLEET_SMOKE=1 uv run --no-sync pytest tests/interface/test_fleet_smoke.py --no-cov -q
"""

from __future__ import annotations

import os
import socket

import pytest

from llm_werewolf.interface.cli.fleet.planner import plan_fleet
from llm_werewolf.interface.cli.fleet.supervisor import ProcessSupervisor

pytestmark = [
    pytest.mark.fleet_smoke,
    pytest.mark.skipif(
        os.environ.get("RUN_FLEET_SMOKE") != "1",
        reason="opt-in: set RUN_FLEET_SMOKE=1 to run the real-subprocess fleet smoke test",
    ),
]


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
