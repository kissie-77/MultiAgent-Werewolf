# change-logger

Project-local Codex skill for keeping task change logs and handoff notes.

## Scope

This copy is installed under `.agents/skills/change-logger/` and uses Codex-side state under `.codex/`.

## What It Creates

- `.codex/current-task` - current task slug.
- `docs/changes/<slug>.md` - task-scoped change table.
- `handoff.md` - generated handoff skeleton, completed by Codex from conversation context.
- `.codex/change-logger.err` - hook errors, if any.

## Commands

```bash
python .agents/skills/change-logger/scripts/start_task.py "<task name>"
python .agents/skills/change-logger/scripts/add_reason.py "<reason>" [--count N] [--task <slug>]
python .agents/skills/change-logger/scripts/generate_handoff.py
```

The optional hook command is:

```bash
python .agents/skills/change-logger/scripts/log_change.py
```

## Daily Flow

1. Start a task with `start_task.py`.
2. After each logical edit chunk, fill trailing `_PENDING_` rows with `add_reason.py`.
3. For handoff, run `generate_handoff.py`, then replace every `<!-- FILL: ... -->` placeholder in `handoff.md`.

## Smoke Test

Run smoke tests in a temporary directory so the repository task state is not changed:

```bash
mkdir %TEMP%\change-logger-smoke
cd %TEMP%\change-logger-smoke
mkdir .codex
python D:\AI_werewolf\MultiAgent-Werewolf-kissie77-20260524\.agents\skills\change-logger\scripts\start_task.py "smoke"
```

Delete the temporary directory when done.
