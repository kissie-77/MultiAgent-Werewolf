"""/ready 就绪探测。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def check_readiness(
    *,
    artifacts_dir: Path | None = None,
    require_ark_key: bool = True,
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

    if require_ark_key:
        ark_ok = bool(os.environ.get("ARK_API_KEY"))
        checks["ark_api_key"] = {"ok": ark_ok, "required": True}
    else:
        checks["ark_api_key"] = {"ok": True, "required": False, "skipped": True}

    failed = [name for name, body in checks.items() if not body.get("ok")]
    status = "ready" if not failed else "not_ready"
    return {
        "status": status,
        "checks": checks,
        "failed": failed,
    }
