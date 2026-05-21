#!/usr/bin/env bash
# Mark serial-agent-call files as skip-worktree so they are not committed by mistake.
set -euo pipefail
cd "$(dirname "$0")/.."

FILES=(
  "src/llm_werewolf/core/engine/night_phase.py"
  "src/llm_werewolf/core/engine/voting_phase.py"
  "src/llm_werewolf/core/engine/sheriff_election.py"
  ".env.example"
)

for f in "${FILES[@]}"; do
  if git ls-files --error-unmatch "$f" &>/dev/null; then
    git update-index --skip-worktree "$f"
    echo "skip-worktree: $f"
  fi
done

echo "Note: src/llm_werewolf/adapter/serial_calls.py is in .gitignore (never add)."
echo "Note: adapter/agent.py has mixed changes — use 'git add -p' before commit."
