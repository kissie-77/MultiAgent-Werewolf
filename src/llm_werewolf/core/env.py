"""Load project ``.env`` from repository root (works regardless of cwd)."""

from __future__ import annotations

from pathlib import Path

import dotenv

_LOADED = False


def find_project_root(start: Path | None = None) -> Path:
    """Return directory containing ``pyproject.toml``, else ``cwd``."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return here


def load_project_dotenv() -> Path | None:
    """Load ``.env`` from repo root once per process. Returns path if file exists."""
    global _LOADED
    if _LOADED:
        return find_project_root() / ".env"

    root = find_project_root()
    env_path = root / ".env"
    if env_path.is_file():
        dotenv.load_dotenv(env_path, override=False)
    else:
        dotenv.load_dotenv(override=False)
    _LOADED = True
    return env_path if env_path.is_file() else None
