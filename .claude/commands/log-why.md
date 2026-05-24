---
description: Backfill the "Why" column for trailing _PENDING_ rows in the current task's change log
---

The user wants to record the reason for recent edits: **$ARGUMENTS**

Run:

```bash
python .claude/skills/change-logger/scripts/add_reason.py "$ARGUMENTS"
```

Then briefly state how many rows were filled. If the script reports 0 rows filled, check whether `.claude/current-task` exists and whether there were any `_PENDING_` entries left.
