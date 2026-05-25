# Codex Hook Setup

The `change-logger` skill can use a PostToolUse hook configured in `.codex/hooks.json`.

## Payload Shape

`log_change.py` expects stdin JSON with this relevant shape:

```json
{
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "src/example.py",
    "old_string": "old",
    "new_string": "new"
  },
  "cwd": "."
}
```

For `Write`, `tool_input` is `{ "file_path": "...", "content": "..." }`.

For `MultiEdit`, `tool_input` is `{ "file_path": "...", "edits": [{ "old_string": "...", "new_string": "..." }] }`.

## Config

Use this command in `.codex/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python .agents/skills/change-logger/scripts/log_change.py"
          }
        ]
      }
    ]
  }
}
```

The command runs with the project root as CWD, so the relative path is intentional.

## Safety

The hook is best-effort. On failure, `log_change.py` writes `.codex/change-logger.err` and exits 0.

The script skips `.codex/`, `.agents/skills/change-logger/`, `docs/changes/`, and `handoff.md` to avoid recursive noise.
