#!/usr/bin/env bash
# Remove skip-worktree from serial-agent-call helper files.
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
    git update-index --no-skip-worktree "$f" 2>/dev/null || true
    echo "no-skip-worktree: $f"
  fi
done
