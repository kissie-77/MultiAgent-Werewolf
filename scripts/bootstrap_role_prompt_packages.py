"""Bootstrap per-role v1 prompt packages from legacy v2 bundle (one-time migration helper)."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
V2_ROLES = ROOT / "src/llm_werewolf/strategy/prompts/v2/roles"
V2_AGENT_BASE = ROOT / "src/llm_werewolf/strategy/prompts/v2/text/agent_base.md"
ROLES_OUT = ROOT / "src/llm_werewolf/strategy/prompts/roles"
SHARED_OUT = ROOT / "src/llm_werewolf/strategy/prompts/shared"
SKILLS_OUT = ROOT / "src/llm_werewolf/agent_team/skills"
VERSION = "v1"


def main() -> None:
    SHARED_OUT.mkdir(parents=True, exist_ok=True)
    if V2_AGENT_BASE.is_file():
        shutil.copy2(V2_AGENT_BASE, SHARED_OUT / "agent_base.md")

    for src in sorted(V2_ROLES.glob("*.yaml")):
        role_key = src.stem
        out_dir = ROLES_OUT / role_key / VERSION
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out_dir / "role.yaml")
        manifest = {
            "role": role_key,
            "version": VERSION,
            "status": "active",
            "parent": None,
            "description": f"Per-role prompt package migrated from v2 bundle",
        }
        (out_dir / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        skill_dir = SKILLS_OUT / role_key / VERSION
        skill_dir.mkdir(parents=True, exist_ok=True)
        keep = skill_dir / ".gitkeep"
        if not any(skill_dir.glob("*.md")):
            keep.write_text("", encoding="utf-8")

    print(f"Bootstrapped {len(list(V2_ROLES.glob('*.yaml')))} role prompt packages at {ROLES_OUT}")


if __name__ == "__main__":
    main()
