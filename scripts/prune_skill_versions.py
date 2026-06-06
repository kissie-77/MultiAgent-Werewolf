"""删除 agent_team/skills 下除 v1 外的所有版本目录。"""

from __future__ import annotations

import shutil
from pathlib import Path

SKILLS_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "llm_werewolf"
    / "agent_team"
    / "skills"
)
KEEP_VERSION = "v1"


def main() -> None:
    removed: list[str] = []
    kept: list[str] = []
    for role_dir in sorted(SKILLS_ROOT.iterdir()):
        if not role_dir.is_dir():
            continue
        for ver_dir in sorted(role_dir.iterdir()):
            if not ver_dir.is_dir():
                continue
            if ver_dir.name == KEEP_VERSION:
                count = len(list(ver_dir.glob("*.md")))
                kept.append(f"{role_dir.name}/{KEEP_VERSION} ({count} skills)")
                continue
            shutil.rmtree(ver_dir)
            removed.append(f"{role_dir.name}/{ver_dir.name}")

    print(f"Removed {len(removed)} version directories:")
    for item in removed:
        print(f"  - {item}")
    print(f"\nKept {len(kept)} v1 directories:")
    for item in kept:
        print(f"  + {item}")


if __name__ == "__main__":
    main()
