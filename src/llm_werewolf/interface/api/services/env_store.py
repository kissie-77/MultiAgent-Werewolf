"""Read/update repository-root ``.env`` for browser-configured LLM API keys."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from llm_werewolf.game_runtime.config.provider_registry import (
    DEFAULT_PROVIDER_ID,
    PROVIDER_REGISTRY,
)
from llm_werewolf.game_runtime.support.env import find_project_root

# Frontend slot name -> process environment variable written to .env
API_KEY_ENV_MAP: dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "doubao": "ARK_API_KEY",
}


def default_env_file_path() -> Path:
    return find_project_root() / ".env"


def mask_secret(value: str) -> str:
    """Return a short masked preview; never echo the full secret."""
    text = value.strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "****"
    return f"{text[:3]}…{text[-4:]}"


def _env_value(env_name: str, on_disk: dict[str, str]) -> str:
    return (os.environ.get(env_name) or on_disk.get(env_name) or "").strip()


def _status_for_env(env_name: str, on_disk: dict[str, str]) -> dict[str, object]:
    value = _env_value(env_name, on_disk)
    return {
        "env_name": env_name,
        "configured": bool(value),
        "masked": mask_secret(value) if value else None,
    }


def read_api_key_status(*, env_path: Path | None = None) -> dict[str, dict[str, object]]:
    """Return per-slot ``configured`` + ``masked`` without exposing full values."""
    path = env_path or default_env_file_path()
    on_disk = _parse_env_file(path) if path.is_file() else {}
    out: dict[str, dict[str, object]] = {}
    for slot, env_name in API_KEY_ENV_MAP.items():
        out[slot] = _status_for_env(env_name, on_disk)
    return out


def read_provider_env_status(*, env_path: Path | None = None) -> dict[str, dict[str, object]]:
    """Status for every env var declared in :data:`PROVIDER_REGISTRY`."""
    path = env_path or default_env_file_path()
    on_disk = _parse_env_file(path) if path.is_file() else {}
    out: dict[str, dict[str, object]] = {}
    for spec in PROVIDER_REGISTRY.values():
        for field in spec.env_fields:
            out[field.env_name] = _status_for_env(field.env_name, on_disk)
    return out


def build_providers_schema() -> list[dict[str, object]]:
    providers: list[dict[str, object]] = []
    for spec in PROVIDER_REGISTRY.values():
        providers.append(
            {
                "provider_id": spec.provider_id,
                "display_name": spec.display_name,
                "fields": [
                    {
                        "env_name": field.env_name,
                        "label": field.label,
                        "required": field.required,
                        "secret": field.secret,
                        "example": field.example,
                        "description": field.description,
                    }
                    for field in spec.env_fields
                ],
            }
        )
    return providers


def upsert_api_keys(
    updates: dict[str, str],
    *,
    env_path: Path | None = None,
) -> list[str]:
    """Merge ``updates`` (env var name -> value) into ``.env`` and ``os.environ``.

    Returns the list of env var names that were written.
    """
    if not updates:
        return []
    path = env_path or default_env_file_path()
    _write_env_file(path, updates)
    for env_name, value in updates.items():
        os.environ[env_name] = value
    return list(updates)


def slot_updates_from_request(payload: dict[str, str | None]) -> dict[str, str]:
    """Map frontend slot fields to env updates; skip empty/whitespace values."""
    out: dict[str, str] = {}
    generic = payload.get("fields")
    if isinstance(generic, dict):
        allowed = {name for spec in PROVIDER_REGISTRY.values() for name in (f.env_name for f in spec.env_fields)}
        for env_name, raw in generic.items():
            if env_name not in allowed or raw is None:
                continue
            value = str(raw).strip()
            if value:
                out[env_name] = value
        if out:
            return out
    for slot, env_name in API_KEY_ENV_MAP.items():
        raw = payload.get(slot)
        if raw is None:
            continue
        value = raw.strip()
        if value:
            out[env_name] = value
    return out


def _parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        parsed[key.strip()] = value.strip().strip('"').strip("'")
    return parsed


def _write_env_file(path: Path, updates: dict[str, str]) -> None:
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    merged: list[str] = []
    seen_keys: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            merged.append(line)
            continue
        key, _, _old = stripped.partition("=")
        key = key.strip()
        if key in remaining:
            merged.append(f"{key}={remaining.pop(key)}")
            seen_keys.add(key)
        else:
            merged.append(line)
            seen_keys.add(key)

    for key, value in remaining.items():
        if key not in seen_keys:
            if merged and merged[-1].strip():
                merged.append("")
            merged.append(f"# Updated via /api/v1/settings/api-keys")
            merged.append(f"{key}={value}")

    text = "\n".join(merged)
    if text:
        text += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".env.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        tmp_path.replace(path)
    finally:
        if tmp_path.is_file():
            tmp_path.unlink(missing_ok=True)
