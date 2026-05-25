---
name: change-logger
description: Use when starting a focused coding task in this werewolf project, after editing code, or when handing off work to another AI (Codex / Claude Code). Maintains docs/changes/<task-slug>.md as an append-only log of every Edit/Write/MultiEdit and assembles handoff.md so the next session can pick up without re-reading the repo. Triggers on phrases like "start task" / "开始任务" / "记录修改" / "交接" / "handoff" / "/start-task" / "/log-why" / "/handoff".
---

# change-logger

Keeps a per-task change log under `docs/changes/<slug>.md` and emits a `handoff.md` at the project root so a follow-up AI can take over without re-reading the entire repository.

## Three operations

1. **Start a task** — pins a slug so subsequent edits are logged into the correct file.
2. **Edits get logged automatically** — a PostToolUse hook (configured in `.claude/settings.local.json`) appends a row per Edit/Write/MultiEdit. The hook captures the **mechanical** info (time, file, lines, tool) and writes `_PENDING_` in the *Why* column because a script cannot infer intent.
3. **Backfill the "Why" + emit handoff** — Claude fills the `_PENDING_` rows after each logical chunk, then runs `generate_handoff.py` and writes the semantic sections of `handoff.md`.

## When to invoke this skill

- User says "start task X" / "/start-task X" / "开始任务 X" → run `scripts/start_task.py`.
- You (Claude) just finished a logical group of edits (one feature, one bugfix, one round of refactor) → run `scripts/add_reason.py "<one-line why>"` **proactively**, before doing the next thing. Don't wait for the user to ask — they're relying on you to keep the log meaningful.
- User says "handoff" / "/handoff" / "交接" / "下班了" → run `scripts/generate_handoff.py`, then read the produced `handoff.md` and fill the `<!-- FILL: ... -->` placeholders using context from the current conversation. The file is useless until you do this.

## Files this skill touches

| Path | Owner | Purpose |
|------|-------|---------|
| `.claude/current-task` | start_task.py writes; hook reads | Plain text, one line, the current task slug. |
| `docs/changes/<slug>.md` | hook appends; add_reason.py edits | Append-only table of every edit in this task. |
| `handoff.md` (project root) | generate_handoff.py writes; Claude edits | Overwritten on each handoff. |

## Starting a task

```bash
python .claude/skills/change-logger/scripts/start_task.py "<freeform task name>"
```

The script slugifies the name (`Fix sheriff voting` → `fix-sheriff-voting`), writes the slug to `.claude/current-task`, and creates `docs/changes/<slug>.md` with a header. If the file already exists it appends a new `## Session N` block instead of clobbering — resuming a task is cheap and safe.

## Backfilling "Why"

After a logical chunk of edits, run:

```bash
python .claude/skills/change-logger/scripts/add_reason.py "<one-line reason>"
```

By default this fills every consecutive `_PENDING_` row at the bottom of the table, stopping at the first already-filled row. Use `--count N` to limit how many rows get this reason (e.g., when you want to attach different reasons to different recent edits).

**Reasons should be honest, not flattering.** "experiment with a quieter noise injection, kept for later comparison" is more useful to the next AI than "improvements". The point is to transfer intent.

If too many `_PENDING_` rows accumulated because you forgot to backfill, walk it back with multiple `add_reason.py --count N "..."` calls in reverse-chronological order.

## Generating handoff.md

```bash
python .claude/skills/change-logger/scripts/generate_handoff.py
```

The script pulls mechanical info — current slug, changed files (from the log), `git status`, recent commits — and emits a `handoff.md` skeleton with placeholder sections marked `<!-- FILL: ... -->`.

**After running the script, read the file and fill the placeholders from conversation context.** Specifically:

- `<!-- FILL: TASK_GOAL -->` — one paragraph: what this task is trying to achieve. Quote the user's wording if they stated it clearly.
- `<!-- FILL: PROGRESS -->` — bullets, done vs pending, with `file:line` where useful.
- `<!-- FILL: KEY_LOCATIONS -->` — 3–7 most important `file:line` pointers (entry point, function under modification, related test).
- `<!-- FILL: BLOCKERS -->` — what's stuck, what you tried that didn't work, things deliberately left alone. Empty if none.
- `<!-- FILL: NEXT_STEPS -->` — ordered list. Pretend you're handing this to a competent stranger who has read the code but not the conversation.

Leave the file in the project root for the next session.

## Why the split between hook and skill

The hook runs deterministically on every tool call and captures things a script can know for certain (which file, which lines, which tool, when). The skill (i.e. you) handles things a script can't know — the reason for the change, the broader task narrative, the next-step priorities.

If the hook ever breaks, the script writes its error to `.claude/change-logger.err` and exits 0 so the session keeps working. The change log degrades gracefully — you lose mechanical entries for that session, but nothing else breaks.

## Common mistakes

- **Editing without `start_task` first.** The hook falls back to `docs/changes/untracked.md`. When you notice, run `start_task` and either move entries over or just leave them under `untracked` as historical noise.
- **Letting `_PENDING_` pile up across unrelated changes.** A single reason covering 30 edits can't be specific enough to be useful. Backfill after each logical chunk, not at the end of the session.
- **Treating `handoff.md` as a chore.** The skeleton handles the boring parts. The placeholders are where the value is. Skipping them leaves the next AI in the same state as starting fresh.
- **Forgetting `handoff.md` exists on the next session.** When the next AI starts in this repo, it should read `handoff.md` first if it exists. Consider mentioning this in `CLAUDE.md` if there is one.

## Files in this skill

- `scripts/log_change.py` — hook entry point (stdin JSON → row in change log).
- `scripts/start_task.py` — pin a task slug.
- `scripts/add_reason.py` — backfill `_PENDING_` rows.
- `scripts/generate_handoff.py` — emit handoff.md skeleton.
- `references/hook-setup.md` — schema notes and instructions to reinstall the hook if `.claude/settings.local.json` is lost.
