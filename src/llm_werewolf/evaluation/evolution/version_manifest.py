from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_werewolf.agent_team.skill_support import skill_loader
from llm_werewolf.agent_team.skill_support.skill_loader import load_role_skills


def write_version_manifest(
    run_dir: str | Path,
    *,
    version_id: str,
    prompt_version: str,
    model: str,
    reasoning_effort: str | None = None,
    memory_runtime_params: dict[str, Any] | None = None,
    prompt_evolution: dict[str, Any] | None = None,
) -> Path:
    base = Path(run_dir)
    payload = {
        "schema": "agent_version_manifest_v1",
        "version_id": version_id,
        "prompt_version": prompt_version,
        "active_skills": _load_active_skills_snapshot(),
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


def restore_active_skills_from_manifest(manifest_path: str | Path) -> None:
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    active_skills = payload.get("active_skills") or {}
    root = skill_loader.agent_skills_root()
    root.mkdir(parents=True, exist_ok=True)

    # Clear existing role skill markdown so the next round reads exactly the inherited active set.
    for role_dir in root.iterdir():
        if role_dir.is_dir():
            for skill_path in role_dir.glob("*.md"):
                skill_path.unlink(missing_ok=True)

    for role, items in active_skills.items():
        role_dir = root / str(role)
        role_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            source_path = Path(str(item.get("path") or ""))
            if not source_path.is_file():
                continue
            target_path = role_dir / source_path.name
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    skill_loader.list_role_skill_files.cache_clear()


def _load_active_skills_snapshot() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for role in ("wolf", "villager", "prophet", "witch", "guard", "hunter", "idiot", "cupid"):
        skills = load_role_skills(role, include_draft=False, max_skills=50)
        if not skills:
            continue
        out[role] = [
            {
                "skill_id": str(skill.get("skill_id") or ""),
                "status": str(skill.get("status") or ""),
                "weight": float(skill.get("weight") or 1.0),
                "description": str(skill.get("description") or ""),
                "path": str(skill.get("path") or ""),
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
