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
    assert "llm_werewolf.interface.api.app" in cmd
    assert "--port" in cmd
    assert "8010" in cmd


def test_build_frontend_command_uses_dev_and_port() -> None:
    specs = plan_fleet(backends=1, frontends=1, be_base=8010, fe_base=5173, require_llm=False)
    cmd = build_frontend_command(specs[0])
    assert "dev" in cmd
    assert "5173" in cmd
