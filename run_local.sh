#!/usr/bin/env bash
# run_local.sh — Launch Kronos Vibe Coder locally with an interactive mode picker.
#
# Usage:
#   ./run_local.sh              (interactive prompt)
#   ./run_local.sh web          (web UI mode)
#   ./run_local.sh api          (API-only mode)
#   ./run_local.sh scan         (one-shot scan; prompts for repo URL)
#   ./run_local.sh docker       (start via Docker Compose)
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
APP="backend.main:app"

# ── helpers ──────────────────────────────────────────────────────────────────

check_python() {
    if ! command -v python3 &>/dev/null; then
        echo "ERROR: python3 not found. Install Python 3.12+." >&2
        exit 1
    fi
}

check_uvicorn() {
    if ! python3 -c "import uvicorn" &>/dev/null; then
        echo "uvicorn not found — installing dependencies…"
        pip install -r requirements.txt
    fi
}

check_docker() {
    if ! command -v docker &>/dev/null; then
        echo "ERROR: docker not found. Install Docker Desktop." >&2
        exit 1
    fi
}

port_in_use() {
    lsof -i :"$1" &>/dev/null 2>&1
}

# ── modes ────────────────────────────────────────────────────────────────────

run_web() {
    check_python
    check_uvicorn
    if port_in_use "$PORT"; then
        echo "Port $PORT already in use. Set PORT=<other> and retry." >&2
        exit 1
    fi
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  Kronos Vibe Coder  –  Web UI mode                  ║"
    echo "║  Open: http://$HOST:$PORT/                           ║"
    echo "║  API docs: http://$HOST:$PORT/docs                   ║"
    echo "╚══════════════════════════════════════════════════════╝"
    python3 -m uvicorn "$APP" --reload --host "$HOST" --port "$PORT"
}

run_api() {
    check_python
    check_uvicorn
    if port_in_use "$PORT"; then
        echo "Port $PORT already in use. Set PORT=<other> and retry." >&2
        exit 1
    fi
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  Kronos Vibe Coder  –  API-only mode                ║"
    echo "║  API docs: http://$HOST:$PORT/docs                   ║"
    echo "╚══════════════════════════════════════════════════════╝"
    python3 -m uvicorn "$APP" --host "$HOST" --port "$PORT"
}

run_scan() {
    check_python
    local repo_url="${REPO_URL:-}"
    if [[ -z "$repo_url" ]]; then
        read -rp "Enter repository URL or local path: " repo_url
    fi
    if [[ -z "$repo_url" ]]; then
        echo "No URL provided. Exiting." >&2
        exit 1
    fi
    echo "Running scan on: $repo_url"
    python3 - <<PYEOF
import json, sys
sys.path.insert(0, '.')
from backend.agents.scan_pipeline import scan_repository
result = scan_repository("$repo_url")
print(json.dumps(result, indent=2, default=str))
PYEOF
}

run_docker() {
    check_docker
    echo "Starting Kronos Vibe Coder via Docker Compose…"
    docker compose up --build
}

# ── main ─────────────────────────────────────────────────────────────────────

MODE="${1:-}"

if [[ -z "$MODE" ]]; then
    echo ""
    echo "Kronos Vibe Coder — local launcher"
    echo "-----------------------------------"
    echo "  1) Web UI      (http://$HOST:$PORT/)"
    echo "  2) API only    (http://$HOST:$PORT/docs)"
    echo "  3) Scan/fix    (one-shot repo analysis)"
    echo "  4) Docker      (docker compose up)"
    echo ""
    read -rp "Pick a mode [1-4]: " CHOICE
    case "$CHOICE" in
        1) MODE="web" ;;
        2) MODE="api" ;;
        3) MODE="scan" ;;
        4) MODE="docker" ;;
        *) echo "Invalid choice." >&2; exit 1 ;;
    esac
fi

case "$MODE" in
    web)    run_web ;;
    api)    run_api ;;
    scan)   run_scan ;;
    docker) run_docker ;;
    *)
        echo "Unknown mode: $MODE" >&2
        echo "Usage: $0 [web|api|scan|docker]" >&2
        exit 1
        ;;
esac
