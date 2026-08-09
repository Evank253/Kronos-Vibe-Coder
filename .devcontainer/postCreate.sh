#!/usr/bin/env bash
# Runs once when the Codespace/devcontainer is created.
#
# Order (enforced by the Vibe Developer <-> Coder contract, see
# backend/vibe_developer_bridge.py):
#   1. Vibe Developer starts first and auto-publishes its dependency contract.
#   2. Kronos-Vibe-Coder (this repo) waits for that contract, aligns its own
#      requirements.txt to it, installs, and runs a smoke test.
#   3. Only if the smoke test passes does anything get committed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACES_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
VIBE_DEVELOPER_DIR="${VIBE_DEVELOPER_DIR:-$WORKSPACES_ROOT/vibe-developer}"
VIBE_DEVELOPER_REPO_URL="${VIBE_DEVELOPER_REPO_URL:-https://github.com/Evank253/vibe-developer.git}"
VIBE_DEVELOPER_URL="${VIBE_DEVELOPER_URL:-http://localhost:4000}"

echo "[postCreate] === Kronos-Vibe-Coder devcontainer setup ==="

echo "[postCreate] installing Kronos-Vibe-Coder Python dependencies..."
pip install -r "$REPO_ROOT/requirements.txt"

# --- 1. Start Vibe Developer first ---------------------------------------
if [ ! -d "$VIBE_DEVELOPER_DIR" ]; then
  echo "[postCreate] cloning Vibe Developer into $VIBE_DEVELOPER_DIR ..."
  git clone --depth 1 "$VIBE_DEVELOPER_REPO_URL" "$VIBE_DEVELOPER_DIR"
fi

echo "[postCreate] installing Vibe Developer dependencies..."
( cd "$VIBE_DEVELOPER_DIR" && npm install )

if [ ! -f "$VIBE_DEVELOPER_DIR/.env" ] && [ -f "$VIBE_DEVELOPER_DIR/.env.example" ]; then
  cp "$VIBE_DEVELOPER_DIR/.env.example" "$VIBE_DEVELOPER_DIR/.env"
fi

echo "[postCreate] starting Vibe Developer in the background (logs: /tmp/vibe-developer.log)..."
( cd "$VIBE_DEVELOPER_DIR" && nohup node server/index.js > /tmp/vibe-developer.log 2>&1 & )

# --- 2. Coder waits for Developer, aligns, smoke-tests --------------------
echo "[postCreate] waiting for Vibe Developer + running dependency alignment..."
export VIBE_DEVELOPER_URL
python "$REPO_ROOT/scripts/align_with_developer.py"

echo "[postCreate] === setup complete ==="
echo "[postCreate] Vibe Developer:      $VIBE_DEVELOPER_URL"
echo "[postCreate] Kronos-Vibe-Coder:   run ./run_server.sh to start on :8080"
