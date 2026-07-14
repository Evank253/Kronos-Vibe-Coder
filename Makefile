.PHONY: help install lint format test build up down logs web api scan

help: ## Show this help message
	@echo "Kronos Vibe Coder – local run targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ── Development ──────────────────────────────────────────────────────────────

install: ## Install Python dependencies into the active venv
	pip install -r requirements.txt
	pip install ruff

lint: ## Run ruff lint checks
	ruff check .

format: ## Auto-format all Python files with ruff
	ruff format .

format-check: ## Check formatting without modifying files
	ruff format --check .

test: ## Run the test suite
	pytest -q

compilecheck: ## Verify Python syntax on the backend package
	python -m compileall backend

ci: lint format-check test compilecheck ## Run the full CI pipeline locally

# ── Run modes ────────────────────────────────────────────────────────────────

web: ## Launch the app with full web UI (default port 8080)
	@echo "Starting Kronos Vibe Coder web UI on http://127.0.0.1:8080 …"
	uvicorn backend.main:app --reload --host 127.0.0.1 --port 8080

api: ## Launch API-only (no static file serving, port 8080)
	@echo "Starting Kronos API on http://127.0.0.1:8080 …"
	uvicorn backend.main:app --host 127.0.0.1 --port 8080

scan: ## Run a one-shot scan against REPO_URL (e.g. make scan REPO_URL=https://github.com/…)
ifndef REPO_URL
	$(error REPO_URL is not set. Usage: make scan REPO_URL=https://github.com/owner/repo)
endif
	@echo "Scanning $(REPO_URL) …"
	python - <<'EOF'
import json
from backend.agents.scan_pipeline import scan_repository
result = scan_repository("$(REPO_URL)")
print(json.dumps(result, indent=2, default=str))
EOF

# ── Docker ───────────────────────────────────────────────────────────────────

build: ## Build the Docker image
	docker compose build

up: ## Start the full stack with Docker Compose
	docker compose up --build

down: ## Stop and remove Docker Compose containers
	docker compose down

logs: ## Follow Docker Compose logs
	docker compose logs -f
