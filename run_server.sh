#!/usr/bin/env bash
set -euo pipefail

PORT=8080
APP_MODULE=backend.main:app

if lsof -i :$PORT >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Please stop the existing process or choose another port."
  exit 1
fi

python3 -m uvicorn "$APP_MODULE" --reload --host 0.0.0.0 --port "$PORT"
