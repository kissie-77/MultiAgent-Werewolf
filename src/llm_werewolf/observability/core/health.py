"""/ready 就绪探测。"""

from __future__ import annotations

import os
from typing import Any
from pathlib import Path

_LLM_KEY_ENVS: tuple[str, ...] = (
    "ARK_API_KEY",
    "OPENAI_API_KEY",
    "VIBE_API_KEY",
    "MOONSHOT_API_KEY",
    "KIMI_API_KEY",
    "ANTHROPIC_API_KEY",
)


def _detect_llm_api_key() -> tuple[bool, str | None]:
    for env_name in _LLM_KEY_ENVS:
        if os.environ.get(env_name, "").strip():
            return True, env_name
    return False, None


def check_readiness(
    *,
    artifacts_dir: Path | None = None,
    require_llm_key: bool = True,
) -> dict[str, Any]:
    """返回 readiness 详情；status=ready 表示通过全部已启用检查。"""
    artifacts_dir = artifacts_dir or Path("artifacts")
    checks: dict[str, dict[str, Any]] = {}

    writable_root = artifacts_dir
    try:
        writable_root.mkdir(parents=True, exist_ok=True)
        probe = writable_root / ".ready_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["artifacts_writable"] = {"ok": True, "path": str(writable_root)}
    except OSError as exc:
        checks["artifacts_writable"] = {"ok": False, "error": str(exc)}

    if require_llm_key:
        llm_ok, matched = _detect_llm_api_key()
        checks["llm_api_key"] = {
            "ok": llm_ok,
            "required": True,
            "matched_env": matched,
            "candidates": list(_LLM_KEY_ENVS),
        }
    else:
        checks["llm_api_key"] = {"ok": True, "required": False, "skipped": True}

    failed = [name for name, body in checks.items() if not body.get("ok")]
    status = "ready" if not failed else "not_ready"
    return {
        "status": status,
        "checks": checks,
        "failed": failed,
    }
