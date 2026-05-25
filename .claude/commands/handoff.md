---
description: Generate handoff.md skeleton and fill the semantic sections from conversation context
---

The user is handing off this task. Follow this sequence:

1. Run the generator:
   ```bash
   python .claude/skills/change-logger/scripts/generate_handoff.py
   ```

2. Read `handoff.md` from the project root.

3. Fill every `<!-- FILL: ... -->` placeholder using context from the current conversation:
   - **TASK_GOAL** — one paragraph: what this task was trying to achieve. Quote the user's wording if they stated it clearly.
   - **PROGRESS** — bullets, done items vs pending items, with `file:line` references where they help.
   - **KEY_LOCATIONS** — 3–7 most important `file:line` pointers. Entry point, function under active modification, related test.
   - **BLOCKERS** — what's stuck, what you tried that didn't work, things deliberately deferred. Empty if none.
   - **NEXT_STEPS** — ordered list. Pretend you're handing this to a competent stranger who has read the code but not the conversation.

4. Save `handoff.md`. Report to the user that the handoff is ready and where the file is.

Do not leave any `<!-- FILL: ... -->` placeholders in the final file — they are mandatory.
