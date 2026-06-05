"""Per-role prompt/skill version manifest for runtime and experiments."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

DEFAULT_PROMPT_VERSION = "latest"
DEFAULT_SKILL_VERSION = "latest"
MANIFEST_FILENAME = "role_version_manifest.json"
_FALLBACK_VERSION = "v1"


def version_sort_key(label: str) -> tuple[int, int, str]:
    """Sort key for version folder names (v2 < v10; unknown labels sort after vN)."""
    text = label.strip().lower()
    if text.startswith("v") and text[1:].isdigit():
        return (0, int(text[1:]), text)
    if text == "baseline":
        return (1, 0, text)
    suffix = text.rsplit("v", 1)
    if len(suffix) == 2 and suffix[1].isdigit():
        return (2, int(suffix[1]), text)
    return (3, 0, text)


def pick_latest_version(versions: Iterable[str], *, fallback: str = _FALLBACK_VERSION) -> str:
    """Return the newest version label, or fallback when none exist."""
    items = [version.strip() for version in versions if str(version).strip()]
    if not items:
        if fallback.strip().lower() == "latest":
            return _FALLBACK_VERSION
        return fallback.strip() or _FALLBACK_VERSION
    return max(items, key=version_sort_key)


def _skills_root() -> Path:
    return Path(__file__).resolve().parents[2] / "agent_team" / "skills"


def list_skill_versions(role_key: str) -> tuple[str, ...]:
    """List on-disk skill version folders for a role (filesystem only, no agent_team import)."""
    role_root = _skills_root() / role_key
    if not role_root.is_dir():
        return ()
    versions = [path.name for path in role_root.iterdir() if path.is_dir()]
    versions.sort(key=version_sort_key)
    return tuple(versions)


@dataclass
class RoleVersionManifest:
    """Maps each prompt_role_key to its prompt and skill version."""

    schema: str = "role_version_manifest_v1"
    default_prompt_version: str = DEFAULT_PROMPT_VERSION
    default_skill_version: str = DEFAULT_SKILL_VERSION
    prompt_versions: dict[str, str] = field(default_factory=dict)
    skill_versions: dict[str, str] = field(default_factory=dict)

    def prompt_version_for(self, role_key: str) -> str:
        if role_key in self.prompt_versions:
            return self.prompt_versions[role_key]
        from llm_werewolf.strategy.registry.role_prompt_registry import list_prompt_versions

        return pick_latest_version(
            list_prompt_versions(role_key),
            fallback=self.default_prompt_version,
        )

    def skill_version_for(self, role_key: str) -> str:
        if role_key in self.skill_versions:
            return self.skill_versions[role_key]
        return pick_latest_version(
            list_skill_versions(role_key),
            fallback=self.default_skill_version,
        )

    def with_prompt_version(self, role_key: str, version: str) -> RoleVersionManifest:
        updated = dict(self.prompt_versions)
        updated[role_key] = version
        return RoleVersionManifest(
            schema=self.schema,
            default_prompt_version=self.default_prompt_version,
            default_skill_version=self.default_skill_version,
            prompt_versions=updated,
            skill_versions=dict(self.skill_versions),
        )

    def with_skill_version(self, role_key: str, version: str) -> RoleVersionManifest:
        updated = dict(self.skill_versions)
        updated[role_key] = version
        return RoleVersionManifest(
            schema=self.schema,
            default_prompt_version=self.default_prompt_version,
            default_skill_version=self.default_skill_version,
            prompt_versions=dict(self.prompt_versions),
            skill_versions=updated,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> RoleVersionManifest:
        if not isinstance(payload, dict):
            return cls()
        return cls(
            schema=str(payload.get("schema") or "role_version_manifest_v1"),
            default_prompt_version=str(
                payload.get("default_prompt_version") or DEFAULT_PROMPT_VERSION
            ),
            default_skill_version=str(
                payload.get("default_skill_version") or DEFAULT_SKILL_VERSION
            ),
            prompt_versions={
                str(k): str(v)
                for k, v in (payload.get("prompt_versions") or {}).items()
                if str(v).strip()
            },
            skill_versions={
                str(k): str(v)
                for k, v in (payload.get("skill_versions") or {}).items()
                if str(v).strip()
            },
        )


_active_manifest: RoleVersionManifest | None = None


def default_manifest() -> RoleVersionManifest:
    return RoleVersionManifest()


def set_active_manifest(manifest: RoleVersionManifest | None) -> None:
    global _active_manifest
    _active_manifest = manifest


def get_active_manifest() -> RoleVersionManifest:
    if _active_manifest is not None:
        return _active_manifest
    return default_manifest()


def load_manifest(path: str | Path) -> RoleVersionManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    manifest = RoleVersionManifest.from_dict(payload)
    return manifest


def write_manifest(path: str | Path, manifest: RoleVersionManifest) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def next_version_label(current: str) -> str:
    """Increment vN labels; fallback append _2, _3 for non-vN names."""
    text = current.strip()
    if text.startswith("v") and text[1:].isdigit():
        return f"v{int(text[1:]) + 1}"
    suffix = 2
    while True:
        candidate = f"{text}_{suffix}"
        suffix += 1
        if candidate != current:
            return candidate
