#!/usr/bin/env bash

# Start local full-stack dev: FastAPI (:8010) + Vite frontend.

# Usage (repo root): ./dev.sh

# Env:             API_PORT=8010 ./dev.sh



set -euo pipefail



ROOT="$(cd "$(dirname "$0")" && pwd)"

API_PORT="${API_PORT:-8010}"

export OBS_READY_REQUIRE_LLM=0

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"



cleanup() {

  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then

    kill "$BACKEND_PID" 2>/dev/null || true

    wait "$BACKEND_PID" 2>/dev/null || true

  fi

}

trap cleanup EXIT INT TERM



cd "$ROOT"



if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then

  echo "Backend already listening on port ${API_PORT} — reusing."

else

  echo "Starting backend on http://127.0.0.1:${API_PORT} ..."

  uv run werewolf-api --port "$API_PORT" &

  BACKEND_PID=$!

  for _ in $(seq 1 90); do

    if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then

      break

    fi

    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then

      echo "Backend exited before becoming healthy." >&2

      exit 1

    fi

    sleep 1

  done

  if ! curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then

    echo "Backend did not become healthy within 90s." >&2

    exit 1

  fi

  echo "Backend ready."

fi



cd "$ROOT/frontend"

if [[ ! -d node_modules ]]; then

  echo "Installing frontend dependencies..."

  npm install

fi



echo "Starting Vite (see frontend/.env.development for API proxy)..."

npm run dev

