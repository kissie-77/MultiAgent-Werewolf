from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_werewolf.agent_team.skill_support import skill_loader
from llm_werewolf.agent_team.skill_support.skill_loader import load_role_skills
from llm_werewolf.strategy.role_version_manifest import (
    RoleVersionManifest,
    get_active_manifest,
    set_active_manifest,
)

_KNOWN_ROLES = (
    "wolf",
    "villager",
    "prophet",
    "witch",
    "guard",
    "hunter",
    "idiot",
    "cupid",
    "wolf_king",
    "white_wolf",
    "wolf_beauty",
    "guardian_wolf",
    "hidden_wolf",
    "nightmare_wolf",
    "blood_moon_apostle",
    "elder",
    "knight",
    "magician",
    "raven",
    "graveyard_keeper",
    "thief",
    "lover",
)


def write_version_manifest(
    run_dir: str | Path,
    *,
    version_id: str,
    prompt_version: str,
    model: str,
    reasoning_effort: str | None = None,
    memory_runtime_params: dict[str, Any] | None = None,
    prompt_evolution: dict[str, Any] | None = None,
    role_version_manifest: RoleVersionManifest | None = None,
) -> Path:
    base = Path(run_dir)
    manifest = role_version_manifest or get_active_manifest()
    payload = {
        "schema": "agent_version_manifest_v2",
        "version_id": version_id,
        "prompt_version": prompt_version,
        "role_version_manifest": manifest.to_dict(),
        "prompt_versions": dict(manifest.prompt_versions),
        "skill_versions": dict(manifest.skill_versions),
        "default_prompt_version": manifest.default_prompt_version,
        "default_skill_version": manifest.default_skill_version,
        "active_skills": _load_active_skills_snapshot(manifest),
        "memory_runtime_params": memory_runtime_params or _default_memory_runtime_params(),
        "model_config": {
            "model": model,
            "reasoning_effort": reasoning_effort,
        },
        "prompt_evolution": prompt_evolution,
    }
    path = base / "version_manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_role_version_manifest_from_file(manifest_path: str | Path) -> RoleVersionManifest:
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    nested = payload.get("role_version_manifest")
    if isinstance(nested, dict):
        return RoleVersionManifest.from_dict(nested)
    return RoleVersionManifest.from_dict(
        {
            "default_prompt_version": payload.get("default_prompt_version") or payload.get("prompt_version"),
            "default_skill_version": payload.get("default_skill_version"),
            "prompt_versions": payload.get("prompt_versions") or {},
            "skill_versions": payload.get("skill_versions") or {},
        }
    )


def restore_runtime_from_manifest(manifest_path: str | Path) -> RoleVersionManifest:
    """Restore active manifest and skill files for the next evolution round."""
    manifest = load_role_version_manifest_from_file(manifest_path)
    set_active_manifest(manifest)
    restore_active_skills_from_manifest(manifest_path, manifest=manifest)
    return manifest


def restore_active_skills_from_manifest(
    manifest_path: str | Path,
    *,
    manifest: RoleVersionManifest | None = None,
) -> None:
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    role_manifest = manifest or load_role_version_manifest_from_file(manifest_path)
    active_skills = payload.get("active_skills") or {}
    root = skill_loader.agent_skills_root()

    for role, items in active_skills.items():
        if not isinstance(items, list):
            continue
        skill_version = role_manifest.skill_version_for(str(role))
        role_dir = root / str(role) / skill_version
        role_dir.mkdir(parents=True, exist_ok=True)
        for existing in role_dir.glob("*.md"):
            existing.unlink(missing_ok=True)
        for item in items:
            source_path = Path(str(item.get("path") or ""))
            if not source_path.is_file():
                continue
            target_path = role_dir / source_path.name
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    skill_loader.list_role_skill_files.cache_clear()


def _load_active_skills_snapshot(manifest: RoleVersionManifest | None = None) -> dict[str, list[dict[str, Any]]]:
    role_manifest = manifest or get_active_manifest()
    out: dict[str, list[dict[str, Any]]] = {}
    for role in _KNOWN_ROLES:
        skill_version = role_manifest.skill_version_for(role)
        skills = load_role_skills(
            role,
            include_draft=False,
            max_skills=50,
            skill_version=skill_version,
        )
        if not skills:
            continue
        out[role] = [
            {
                "skill_id": str(skill.get("skill_id") or ""),
                "status": str(skill.get("status") or ""),
                "weight": float(skill.get("weight") or 1.0),
                "description": str(skill.get("description") or ""),
                "path": str(skill.get("path") or ""),
                "skill_version": skill_version,
            }
            for skill in skills
        ]
    return out


def _default_memory_runtime_params() -> dict[str, Any]:
    return {
        "skill_top_k": 5,
        "semantic_top_k": 3,
        "similarity_threshold": 0.78,
        "working_compression_enabled": False,
    }
