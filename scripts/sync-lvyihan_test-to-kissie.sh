#!/usr/bin/env bash
# Push current lvyihan_test to kissie-77/MultiAgent-Werewolf (requires your PAT).
set -euo pipefail

if [[ -z "${KISSIE_GITHUB_TOKEN:-}" ]]; then
  echo "Set KISSIE_GITHUB_TOKEN to a kissie-77 classic PAT with repo scope." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
git fetch origin lvyihan_test
git checkout lvyihan_test
git pull origin lvyihan_test

UPSTREAM="https://x-access-token:${KISSIE_GITHUB_TOKEN}@github.com/kissie-77/MultiAgent-Werewolf.git"
git remote remove kissie 2>/dev/null || true
git remote add kissie "$UPSTREAM"
git push kissie HEAD:refs/heads/lvyihan_test --force-with-lease
echo "Done: https://github.com/kissie-77/MultiAgent-Werewolf/tree/lvyihan_test"
