#!/usr/bin/env python3
"""Pin a task slug for change-logger.

Usage:
    python start_task.py "Fix sheriff voting bug"

Writes the slug to .codex/current-task and creates docs/changes/<slug>.md
with a markdown table header. If the file already exists, appends a new
"## Session N" block rather than overwriting; resuming a task is safe.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path


def slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")
    return name or "untitled"


def find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".codex").exists() or (p / ".agents").exists() or (p / ".git").exists():
            return p
    return cur


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: start_task.py <task name>", file=sys.stderr)
        return 2

    raw = " ".join(sys.argv[1:]).strip()
    if not raw:
        print("task name cannot be empty", file=sys.stderr)
        return 2

    slug = slugify(raw)
    root = find_project_root(Path.cwd())

    codex_dir = root / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    (codex_dir / "current-task").write_text(slug + "\n", encoding="utf-8")

    changes_dir = root / "docs" / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)
    log_file = changes_dir / f"{slug}.md"

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not log_file.exists():
        header = (
            f"# Changes: {slug}\n\n"
            f"> Task name: {raw}\n"
            f"> Started: {now}\n"
            f"> Tracked via `.agents/skills/change-logger`\n\n"
            f"## Session 1 - {now}\n\n"
            f"| Time | Tool | File | Lines | Why |\n"
            f"|------|------|------|-------|-----|\n"
        )
        log_file.write_text(header, encoding="utf-8")
        print(f"created docs/changes/{slug}.md  (slug: {slug})")
    else:
        existing = log_file.read_text(encoding="utf-8")
        n = len(re.findall(r"^## Session \d+", existing, flags=re.MULTILINE)) + 1
        addon = (
            f"\n## Session {n} - {now}\n\n"
            f"| Time | Tool | File | Lines | Why |\n"
            f"|------|------|------|-------|-----|\n"
        )
        log_file.write_text(existing.rstrip() + "\n" + addon, encoding="utf-8")
        print(f"resumed docs/changes/{slug}.md as session {n}  (slug: {slug})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
