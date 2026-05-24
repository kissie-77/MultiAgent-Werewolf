"""从仓库根目录加载项目 ``.env``（与当前工作目录无关）。"""

from __future__ import annotations

from pathlib import Path

import dotenv

_LOADED = False
_LOADED_ENV_PATH: Path | None = None


def find_project_root(start: Path | None = None) -> Path:
    """返回包含 ``pyproject.toml`` 的目录，否则返回 ``cwd``。"""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return here


def load_project_dotenv() -> Path | None:
    """每个进程仅从仓库根目录加载一次 ``.env``。若文件存在则返回其路径。"""
    global _LOADED, _LOADED_ENV_PATH
    if _LOADED:
        return _LOADED_ENV_PATH

    root = find_project_root()
    env_path = root / ".env"
    if env_path.is_file():
        dotenv.load_dotenv(env_path, override=False)
    else:
        dotenv.load_dotenv(override=False)
    _LOADED = True
    _LOADED_ENV_PATH = env_path if env_path.is_file() else None
    return _LOADED_ENV_PATH
