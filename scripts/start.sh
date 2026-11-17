#!/bin/sh
set -e
cd "$(dirname "$0")/.."
.venv/bin/uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM
sleep 1
if ! kill -0 "$API_PID" 2>/dev/null; then
  echo "Backend could not start. Check that port 8000 is available." >&2
  exit 1
fi
node node_modules/vite/bin/vite.js --host "${WEB_HOST:-127.0.0.1}" --port "${WEB_PORT:-5173}"
