# Kronos Vibe Coder

An AI-powered code analysis, error-fixing, and deployment assistant built with FastAPI.
Load any repository, run checks (lint + tests + static analysis), get a plain-language
error summary, and receive patch-ready fix suggestions powered by any OpenAI-compatible
LLM provider.

---

## Quick start

### Option A — venv / pip

```bash
# 1. Clone and create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install ruff          # for the lint/format checks

# 3. Copy and configure environment variables
cp .env.example .env
# Edit .env – set SESSION_SECRET and optionally AI_API_KEY

# 4. Launch (interactive mode picker)
./run_local.sh
```

### Option B — Docker Compose

```bash
cp .env.example .env
# Edit .env – set SESSION_SECRET and optionally AI_API_KEY

docker compose up --build
```

The app runs on **http://127.0.0.1:8080** (venv) or **http://localhost:8000** (Docker).

---

## Run modes

| Mode | Command | Description |
|------|---------|-------------|
| Interactive | `./run_local.sh` | Prompts you to pick a mode |
| Web UI | `./run_local.sh web` or `make web` | Full web UI + API |
| API only | `./run_local.sh api` or `make api` | FastAPI only, no static files |
| One-shot scan | `./run_local.sh scan` or `make scan REPO_URL=…` | CLI scan of a repo |
| Docker | `./run_local.sh docker` or `make up` | Docker Compose stack |

---

## How the analyze → fix flow works

1. **Analyze** – POST `/chatbot/analyze` with `{"path": "/local/path"}` or use the Web UI.
   The server runs `ruff check` (lint) and `pytest` (tests) and returns a structured summary.

2. **Suggest fixes** – POST `/suggest-fixes` with the analysis result.
   If `AI_API_KEY` is set, the server calls the configured LLM and returns markdown-formatted
   fix suggestions with before/after code snippets.
   Without an API key, a rule-based summary is returned.

3. **Review & apply** – Read the diff/patch guidance in the suggestions.
   **Always review diffs before applying them to production code.**

4. **Deploy** – Use the Submit Repo tab to run the full scan pipeline, then click
   "Deploy" to create a branch and open a Pull Request via GitHub OAuth.

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| POST | `/chatbot/analyze` | Lint + test a local path |
| POST | `/suggest-fixes` | LLM fix suggestions from analysis result |
| POST | `/analyze` | Repo file tree analysis |
| POST | `/scan_repo` | Clone + full pipeline scan |
| POST | `/submit_project` | Async scan job submission |
| GET | `/job_status/{id}` | Poll async job status |
| POST | `/deploy_confirm` | Create branch + PR via GitHub |
| GET | `/docs` | Interactive Swagger UI |

---

## LLM / AI provider configuration

Set these in `.env` (see `.env.example` for full documentation):

```
AI_BASE_URL=https://api.openai.com/v1   # or Azure / Ollama endpoint
AI_API_KEY=sk-...                        # leave blank for rule-based only
AI_MODEL=gpt-4o-mini
```

Supported providers: OpenAI, Azure OpenAI, Ollama (local), any OpenAI-compatible API.

---

## GitHub OAuth / Login

Required to use the "Deploy" feature (create branch + PR):

1. Go to GitHub Settings → Developer settings → OAuth Apps → New OAuth App.
2. Set the callback URL to `http://127.0.0.1:8080/github/callback`.
3. Copy the Client ID and Secret into `.env`.

See `DEPLOY.md` for full setup instructions.

---

## Development

```bash
# Lint
make lint

# Auto-format
make format

# Tests
make test

# Full CI pipeline (lint + format-check + test + compile)
make ci
```

CI uses **Ruff** (replaces flake8) with `line-length = 79` and `select = ["E", "F"]`.

---

## Limitations & safety notes

- Fix suggestions are AI-generated and **must be reviewed** before applying.
  Never auto-apply patches to production without human review.
- The "Deploy" flow commits to a new branch and opens a PR — it does not merge automatically.
- This is a prototype: the fix agent generates summary files, not full automated patches.
  Extend `backend/agents/fix_agent.py` to produce real file diffs.
- For production use, replace the in-memory session store and SQLite job DB with
  persistent backends, and use a strong `SESSION_SECRET`.


