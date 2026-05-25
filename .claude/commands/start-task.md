---
description: Pin a task slug for change-logger and create docs/changes/<slug>.md
---

The user wants to start a new tracked task: **$ARGUMENTS**

Run:

```bash
python .claude/skills/change-logger/scripts/start_task.py "$ARGUMENTS"
```

Then briefly report which slug was set and which file was created or resumed. Remind the user that after each logical chunk of edits you'll backfill the "Why" column via `/log-why "..."` (or `add_reason.py` directly), and that `/handoff` will generate the handoff doc when they're ready to hand off.
