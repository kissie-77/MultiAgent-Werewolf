"""Shared fixtures for interface / API tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from llm_werewolf.interface.api.app import create_app
from llm_werewolf.interface.api.deps import get_configs_dir, get_eval_runs_dir, get_runs_dir

from fixtures import write_demo_config, write_sample_run


@pytest.fixture
def api_dirs(tmp_path: Path) -> dict[str, Path]:
    runs_dir = tmp_path / "artifacts" / "runs"
    eval_runs_dir = tmp_path / "artifacts" / "eval_runs"
    configs_dir = tmp_path / "configs"
    runs_dir.mkdir(parents=True)
    eval_runs_dir.mkdir(parents=True)
    write_demo_config(configs_dir)
    write_sample_run(runs_dir / "test-run-1")
    eval_batch = eval_runs_dir / "batch-001" / "games"
    write_sample_run(eval_batch / "eval-run-1")
    return {
        "root": tmp_path,
        "runs_dir": runs_dir,
        "eval_runs_dir": eval_runs_dir,
        "configs_dir": configs_dir,
    }


@pytest.fixture
def api_client(api_dirs: dict[str, Path]) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_runs_dir] = lambda: api_dirs["runs_dir"]
    app.dependency_overrides[get_eval_runs_dir] = lambda: api_dirs["eval_runs_dir"]
    app.dependency_overrides[get_configs_dir] = lambda: api_dirs["configs_dir"]
    with TestClient(app) as client:
        yield client
