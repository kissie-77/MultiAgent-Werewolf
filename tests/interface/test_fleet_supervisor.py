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
