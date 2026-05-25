#!/usr/bin/env python3
"""PostToolUse hook entry point for change-logger.

Reads the Claude Code hook payload from stdin and appends a row to
docs/changes/<current-task>.md describing the edit. Silent on success;
failures are written to .claude/change-logger.err and the script still
exits 0 so a broken hook never wedges a session.

Hook payload (relevant subset):
{
  "tool_name": "Edit" | "Write" | "MultiEdit",
  "tool_input": {
    "file_path": "...",
    # Edit:
    "old_string": "...", "new_string": "...",
    # Write:
    "content": "...",
    # MultiEdit:
    "edits": [{"old_string": "...", "new_string": "..."}, ...]
  },
  "cwd": "..."
}
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path


TRACKED_TOOLS = {"Edit", "Write", "MultiEdit"}


def project_root(cwd: str) -> Path:
    p = Path(cwd).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".claude").exists() or (cand / ".git").exists():
            return cand
    return p


def relpath(file_path: str, root: Path) -> str:
    try:
        return str(Path(file_path).resolve().relative_to(root)).replace("\\", "/")
    except (ValueError, OSError):
        return file_path.replace("\\", "/")


def find_lines_post(file_path: str, needle: str) -> str:
    """Find the line range of `needle` in the (post-edit) file."""
    if not needle:
        return "?"
    try:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "?"
    idx = text.find(needle)
    if idx < 0:
        return "?"
    start = text.count("\n", 0, idx) + 1
    end = start + needle.count("\n")
    return f"L{start}-L{end}" if end > start else f"L{start}"


def lines_for_write(content: str) -> str:
    n = content.count("\n") + (0 if content.endswith("\n") else 1)
    n = max(n, 1)
    return f"L1-L{n}" if n > 1 else "L1"


def ensure_log_file(log_file: Path, slug: str) -> None:
    if log_file.exists():
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"# Changes: {slug}\n\n"
        f"> Auto-created by change-logger hook on {now}\n"
        f"> (start_task.py was not run before edits — consider running it to attach a real task name)\n\n"
        f"| Time | Tool | File | Lines | Why |\n"
        f"|------|------|------|-------|-----|\n"
    )
    log_file.write_text(header, encoding="utf-8")


def log_err(root: Path, msg: str) -> None:
    try:
        (root / ".claude").mkdir(parents=True, exist_ok=True)
        with (root / ".claude" / "change-logger.err").open("a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now().isoformat()} {msg}\n")
    except OSError:
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in TRACKED_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    cwd = payload.get("cwd") or os.getcwd()
    root = project_root(cwd)

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    rel = relpath(file_path, root)
    # Skip our own files to avoid recursion noise.
    if rel.startswith(".claude/") or rel.startswith("docs/changes/") or rel == "handoff.md":
        return 0

    task_file = root / ".claude" / "current-task"
    slug = task_file.read_text(encoding="utf-8").strip() if task_file.exists() else ""
    slug = slug or "untracked"

    log_file = root / "docs" / "changes" / f"{slug}.md"
    now = dt.datetime.now().strftime("%H:%M:%S")

    rows: list[str] = []
    if tool_name == "Edit":
        new = tool_input.get("new_string", "")
        rows.append(f"| {now} | Edit | `{rel}` | {find_lines_post(file_path, new)} | _PENDING_ |")
    elif tool_name == "Write":
        content = tool_input.get("content", "")
        rows.append(f"| {now} | Write | `{rel}` | {lines_for_write(content)} | _PENDING_ |")
    elif tool_name == "MultiEdit":
        for e in tool_input.get("edits") or []:
            new = e.get("new_string", "")
            rows.append(f"| {now} | MultiEdit | `{rel}` | {find_lines_post(file_path, new)} | _PENDING_ |")

    if not rows:
        return 0

    try:
        ensure_log_file(log_file, slug)
        with log_file.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(r + "\n")
    except OSError as exc:
        log_err(root, f"append failed: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
