#!/usr/bin/env python3
"""Backfill the 'Why' column for trailing _PENDING_ rows.

Usage:
    python add_reason.py "<one-line reason>"
    python add_reason.py "<reason>" --count 3
    python add_reason.py "<reason>" --task other-slug
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".codex").exists() or (p / ".agents").exists() or (p / ".git").exists():
            return p
    return cur


DATA_ROW_RE = re.compile(r"^\|\s*\d{2}:\d{2}:\d{2}\s*\|")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reason", help="One-line reason text (markdown pipes will be escaped)")
    ap.add_argument(
        "--count",
        type=int,
        default=0,
        help="Limit how many _PENDING_ rows to fill (default: all trailing pending rows, stopping at the first filled row)",
    )
    ap.add_argument("--task", default=None, help="Override task slug (default: read from .codex/current-task)")
    args = ap.parse_args()

    root = find_project_root(Path.cwd())

    slug = args.task
    if not slug:
        task_file = root / ".codex" / "current-task"
        if not task_file.exists():
            print("no .codex/current-task - run start_task.py first or pass --task", file=sys.stderr)
            return 1
        slug = task_file.read_text(encoding="utf-8").strip()

    log_file = root / "docs" / "changes" / f"{slug}.md"
    if not log_file.exists():
        print(f"no log file at docs/changes/{slug}.md", file=sys.stderr)
        return 1

    lines = log_file.read_text(encoding="utf-8").splitlines()
    reason = args.reason.replace("|", "\\|").replace("\n", " ").strip()
    if not reason:
        print("reason is empty", file=sys.stderr)
        return 2

    filled = 0
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if "_PENDING_" in line:
            lines[i] = line.replace("_PENDING_", reason)
            filled += 1
            if args.count and filled >= args.count:
                break
            continue
        if args.count:
            continue
        if DATA_ROW_RE.match(line):
            break

    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"filled {filled} row(s) in docs/changes/{slug}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
