#!/usr/bin/env python3
"""Generate a handoff.md skeleton in the project root.

Pulls mechanical info from docs/changes/<slug>.md, git status, git log,
then writes a markdown file with placeholder sections (`<!-- FILL: ... -->`)
for Claude or a human to fill semantically.

Usage:
    python generate_handoff.py
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path


def find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".claude").exists() or (p / ".git").exists():
            return p
    return cur


def git(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        return out.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def extract_changed_files(log_text: str) -> list[str]:
    files: list[str] = []
    for line in log_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5:
            continue
        if cols[0] in ("Time",) or cols[0].startswith("-"):
            continue
        m = re.search(r"`([^`]+)`", cols[2])
        if m:
            files.append(m.group(1))
    seen: set[str] = set()
    out: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def main() -> int:
    root = find_project_root(Path.cwd())
    task_file = root / ".claude" / "current-task"
    slug = task_file.read_text(encoding="utf-8").strip() if task_file.exists() else ""

    log_text = ""
    if slug:
        log_path = root / "docs" / "changes" / f"{slug}.md"
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8")

    changed_files = extract_changed_files(log_text)
    git_status = git(["status", "--short"], root).strip()
    git_log = git(["log", "--oneline", "-n", "15"], root).strip()
    git_branch = git(["rev-parse", "--abbrev-ref", "HEAD"], root).strip() or "?"

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts: list[str] = []
    parts.append(f"# Handoff — {slug or '(no task pinned)'}")
    parts.append("")
    parts.append(f"> Generated: {now}")
    parts.append(f"> Branch: `{git_branch}`")
    if slug:
        parts.append(f"> Change log: [docs/changes/{slug}.md](docs/changes/{slug}.md)")
    parts.append("")
    parts.append("## Task goal & progress")
    parts.append("")
    parts.append("<!-- FILL: TASK_GOAL — one paragraph, what this task is trying to achieve. Quote the user's own words if they were clear. -->")
    parts.append("")
    parts.append("**Status:**")
    parts.append("")
    parts.append("<!-- FILL: PROGRESS — bullets, done items / pending items. Be specific (file:line) where useful. -->")
    parts.append("")
    parts.append("## Files changed this task")
    parts.append("")
    if changed_files:
        for f in changed_files:
            parts.append(f"- `{f}`")
    else:
        parts.append("_(no entries in change log — either the task just started or the hook didn't fire)_")
    parts.append("")
    parts.append("## Key code locations")
    parts.append("")
    parts.append("<!-- FILL: KEY_LOCATIONS — 3-7 most important file:line pointers. Entry points, the function under active modification, the test file. -->")
    parts.append("")
    parts.append("## Git status")
    parts.append("")
    parts.append("```")
    parts.append(git_status or "(clean)")
    parts.append("```")
    parts.append("")
    parts.append("## Recent commits")
    parts.append("")
    parts.append("```")
    parts.append(git_log or "(no commits)")
    parts.append("```")
    parts.append("")
    parts.append("## Blockers / known issues")
    parts.append("")
    parts.append("<!-- FILL: BLOCKERS — what's stuck, what you tried that didn't work, deliberately deferred items. Empty if none. -->")
    parts.append("")
    parts.append("## Next steps")
    parts.append("")
    parts.append("<!-- FILL: NEXT_STEPS — ordered list. Pretend you're handing this to a competent stranger who has read the code but not the conversation. -->")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("_Skeleton from `.claude/skills/change-logger/scripts/generate_handoff.py`. Sections marked `<!-- FILL: ... -->` must be filled before this handoff is useful to the next AI._")
    parts.append("")

    out = root / "handoff.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote handoff.md  ({len(changed_files)} file(s) from change log)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
