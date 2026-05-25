# Hook setup notes

The `change-logger` skill depends on a PostToolUse hook configured in `.claude/settings.local.json`. The setup script installed it automatically; this file documents the schema so it can be reinstalled if the settings file is lost.

## What the hook does

For every `Edit`, `Write`, or `MultiEdit` tool call, Claude Code invokes `scripts/log_change.py` and pipes the tool payload to it via stdin. The script appends a row to `docs/changes/<current-task>.md`. It is silent on success and writes any errors to `.claude/change-logger.err` while still exiting 0, so a broken hook never wedges a session.

## Schema (Claude Code hook payload, stdin)

```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "<project root>",
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "...",
    "old_string": "...",
    "new_string": "..."
  },
  "tool_response": { ... }
}
```

For `Write`: `tool_input` is `{file_path, content}`.

For `MultiEdit`: `tool_input` is `{file_path, edits: [{old_string, new_string, replace_all}, ...]}`.

## Settings snippet

Drop this into `.claude/settings.local.json` under the `hooks` key:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/skills/change-logger/scripts/log_change.py"
          }
        ]
      }
    ]
  }
}
```

The command runs with the project root as CWD (Claude Code resolves the settings file from the project root), so a relative path is correct.

## Sanity test

Pipe a fake payload into the script and verify a row lands in the right file:

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"README.md","content":"hello\nworld\n"},"cwd":"."}' \
  | python .claude/skills/change-logger/scripts/log_change.py
```

Then check `docs/changes/<your-current-task>.md` (or `docs/changes/untracked.md` if no task is pinned).

## Disabling temporarily

Either remove the hook block from `.claude/settings.local.json`, or rename the script (so the hook fails silently and the error file collects the misses). The skill itself stays usable for manual logging via `add_reason.py` and `generate_handoff.py`.
