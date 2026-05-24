---
name: source-command-handoff
description: Use when the user asks to run the migrated source command "handoff", "/handoff", or prepare a task handoff in this Codex project.
---

# source-command-handoff

Use this skill when the user asks to run the migrated source command `handoff`.

## Command Template

The user is handing off this task. Follow this sequence:

1. Run the generator:

   ```bash
   python .agents/skills/change-logger/scripts/generate_handoff.py
   ```

2. Read `handoff.md` from the project root.

3. Fill every `<!-- FILL: ... -->` placeholder using context from the current conversation:

   - **TASK_GOAL** - one paragraph: what this task was trying to achieve. Quote the user's wording if they stated it clearly.
   - **PROGRESS** - bullets, done items vs pending items, with `file:line` references where they help.
   - **KEY_LOCATIONS** - 3-7 most important `file:line` pointers. Entry point, function under active modification, related test.
   - **BLOCKERS** - what is stuck, what you tried that did not work, things deliberately deferred. Empty if none.
   - **NEXT_STEPS** - ordered list. Pretend you are handing this to a competent stranger who has read the code but not the conversation.

4. Save `handoff.md`. Report to the user that the handoff is ready and where the file is.

Do not leave any `<!-- FILL: ... -->` placeholders in the final file. They are mandatory.
