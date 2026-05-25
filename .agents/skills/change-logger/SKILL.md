---
name: change-logger
description: Use when starting a focused coding task in this werewolf project, recording why recent edits were made, or preparing a handoff for another Codex session. Triggers include "start task", "开始任务", "记录修改", "交接", "handoff", "/start-task", "/log-why", and "/handoff".
---

# change-logger

Codex project skill for keeping a task-scoped change narrative. State lives in `.codex/current-task`; reusable scripts live in `.agents/skills/change-logger/scripts`.

## Three operations

1. **Start a task** - pin a slug so subsequent logs use the right file.
2. **Capture changed files** - the optional hook appends mechanical rows with `_PENDING_` in the Why column.
3. **Backfill intent and hand off** - Codex fills `_PENDING_` rows after each logical chunk, then generates and completes `handoff.md` when needed.

## When to invoke this skill

- User says "start task X", "/start-task X", or "开始任务 X": run `scripts/start_task.py`.
- Codex just finished a logical group of edits: run `scripts/add_reason.py "<one-line why>"` before moving on.
- User says "handoff", "/handoff", "交接", or "下班了": run `scripts/generate_handoff.py`, then fill every `<!-- FILL: ... -->` placeholder in `handoff.md`.

## Files this skill touches

| Path | Owner | Purpose |
|------|-------|---------|
| `.codex/current-task` | start_task.py writes; hook reads | Plain text, one line, the current task slug. |
| `docs/changes/<slug>.md` | hook appends; add_reason.py edits | Append-only table of every edit in this task. |
| `handoff.md` | generate_handoff.py writes; Codex edits | Overwritten on each handoff. |
| `.codex/hooks.json` | optional Codex hook config | Points hook events at the `.agents` scripts. |

## Starting a task

```bash
python .agents/skills/change-logger/scripts/start_task.py "<freeform task name>"
```

The script slugifies the name (`Fix sheriff voting` -> `fix-sheriff-voting`), writes the slug to `.codex/current-task`, and creates `docs/changes/<slug>.md` with a header. If the file already exists it appends a new `## Session N` block instead of overwriting it.

## Backfilling Why

After a logical chunk of edits, run:

```bash
python .agents/skills/change-logger/scripts/add_reason.py "<one-line reason>"
```

By default this fills every consecutive `_PENDING_` row at the bottom of the table, stopping at the first already-filled row. Use `--count N` to limit how many rows get this reason.

Reasons should be honest and specific. "experiment with a quieter noise injection, kept for later comparison" is more useful to the next session than "improvements".

If too many `_PENDING_` rows accumulated, use multiple `add_reason.py --count N "..."` calls in reverse-chronological order.

## Generating handoff.md

```bash
python .agents/skills/change-logger/scripts/generate_handoff.py
```

The script pulls mechanical info - current slug, changed files from the log, `git status`, and recent commits - then emits a `handoff.md` skeleton with placeholder sections marked `<!-- FILL: ... -->`.

After running the script, read the file and fill the placeholders from conversation context:

- `<!-- FILL: TASK_GOAL -->` - one paragraph describing the goal. Quote the user's wording if it was clear.
- `<!-- FILL: PROGRESS -->` - done vs pending bullets, with `file:line` where useful.
- `<!-- FILL: KEY_LOCATIONS -->` - 3-7 important `file:line` pointers.
- `<!-- FILL: BLOCKERS -->` - what is stuck, what failed, and what was deliberately left alone. Empty if none.
- `<!-- FILL: NEXT_STEPS -->` - ordered list for the next session.

Leave the file in the project root for the next session.

## Why the split between hook and skill

The hook captures things a script can know for certain: file, line range, tool, and time. The skill handles things a script cannot know: the reason for the change, the broader task narrative, and next-step priorities.

If the hook breaks, the script writes its error to `.codex/change-logger.err` and exits 0 so the session keeps working. The change log degrades gracefully: mechanical rows may be missing, but nothing else breaks.

## Common mistakes

- **Editing without `start_task` first.** The hook falls back to `docs/changes/untracked.md`. When you notice, run `start_task` and either move entries over or leave them under `untracked` as historical noise.
- **Letting `_PENDING_` pile up across unrelated changes.** Backfill after each logical chunk, not only at the end of the session.
- **Leaving handoff placeholders.** A generated `handoff.md` is not useful until every `<!-- FILL: ... -->` placeholder is replaced.
- **Assuming automatic capture is always active.** The scripts work manually even if the optional hook is not active.

## Files in this skill

- `scripts/log_change.py` - hook entry point (stdin JSON -> row in change log).
- `scripts/start_task.py` - pin a task slug.
- `scripts/add_reason.py` - backfill `_PENDING_` rows.
- `scripts/generate_handoff.py` - emit `handoff.md` skeleton.
- `references/hook-setup.md` - schema notes and instructions to reinstall the `.codex/hooks.json` hook.
