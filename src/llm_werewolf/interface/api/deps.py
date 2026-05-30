"""FastAPI dependencies."""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.paths import ARTIFACTS_DIR, EVAL_RUNS_DIR, RUNS_DIR


def get_project_root() -> Path:
    """Return repository root (cwd when started via CLI)."""
    return Path.cwd()


def get_runs_dir() -> Path:
    return get_project_root() / RUNS_DIR


def get_eval_runs_dir() -> Path:
    return get_project_root() / EVAL_RUNS_DIR


def get_artifacts_dir() -> Path:
    return get_project_root() / ARTIFACTS_DIR


def get_configs_dir() -> Path:
    return get_project_root() / "configs"
