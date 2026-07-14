from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from backend.csrf import CSRFMiddleware, ensure_csrf_in_session
import os
import logging
from backend.session_store import RedisSessionStore
import threading
import uuid
import requests
from github import Github
from typing import List

from backend.agents.repo_analyzer import analyze_repo
from backend.agents.debug_agent import debug_project
from backend.agents.scan_pipeline import scan_repository
from backend.agents.deploy_agent import (
    deployment_check,
    generate_deployment_plan,
)
from backend.agents.deployment_manager import (
    build_check,
    deployment_config,
    release_approval,
)
from backend.agents.fix_agent import generate_fix_plan, apply_fix_plan
from backend.agents.chatbot_agent import analyze_path, suggest_fixes
from backend.jobs import init_db, create_job, update_job_status, get_job
from backend.agents.github_manager import (
    create_branch,
    commit_changes,
    open_pull_request,
)

app = FastAPI(title="Kronos Vibe Coder")

# Sessions (tokens are stored per-user in session after OAuth)
SECRET_KEY = os.getenv("SESSION_SECRET", "dev-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
# add CSRF middleware after sessions
app.add_middleware(CSRFMiddleware)

# Serve a small frontend under /ui
if os.path.isdir("/workspaces/Kronos-Vibe-Coder/static"):
    app.mount(
        "/static",
        StaticFiles(directory="/workspaces/Kronos-Vibe-Coder/static"),
        name="static",
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    index_path = "/workspaces/Kronos-Vibe-Coder/static/index.html"
    try:
        with open(index_path, "r") as f:
            return HTMLResponse(f.read())
    except Exception:
        return {"name": "Kronos Vibe Coder", "status": "online"}


@app.get("/health")
def health():
    return {"status": "ok"}


# In-memory job store for submissions (prototype)
JOBS = {}

# Initialize persistent job DB
init_db()

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("kronos")

# Optional Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk

        sentry_sdk.init(SENTRY_DSN)
        logger.info("Sentry initialized")
    except Exception:
        logger.exception("Failed to initialize Sentry")

# Redis session store if configured
SESSION_STORE = None
if os.getenv("REDIS_URL"):
    try:
        SESSION_STORE = RedisSessionStore()
        logger.info("Using Redis session store")
    except Exception:
        logger.exception("Failed to initialize Redis session store")

# Set to True via HTTPS_ONLY=1 in production so session cookies get secure flag
_SECURE_COOKIES = os.getenv("HTTPS_ONLY", "0") == "1"


@app.get("/healthz")
def healthz():
    """Health check endpoint for container orchestration."""
    return {"status": "ok"}


@app.post("/analyze")
def analyze(data: dict):
    repo = data.get("repo", ".")
    return analyze_repo(repo)


@app.post("/chatbot/analyze")
def chatbot_analyze(data: dict):
    """Analyze a local path or cloned repo; run lint + tests."""
    path = data.get("path") or data.get("repo", ".")
    return analyze_path(path)


@app.post("/suggest-fixes")
def suggest_fixes_endpoint(data: dict):
    """Given a prior /chatbot/analyze result, produce LLM fix suggestions."""
    return suggest_fixes(data)


@app.post("/debug")
def debug(data: dict):
    return debug_project(data)


@app.post("/scan_repo")
def scan_repo(data: dict):
    repo_url = data.get("url")
    if not repo_url:
        raise HTTPException(status_code=400, detail="Repository URL required")

    try:
        return scan_repository(repo_url)
    except Exception:
        logger.exception("scan_repo failed for %s", repo_url)
        raise HTTPException(status_code=500, detail="Repository scan failed")


@app.post("/github/create_branch")
def github_create_branch(data: dict):
    repo = data.get("repo")
    branch = data.get("branch")
    base = data.get("base", "main")

    if not repo or not branch:
        raise HTTPException(
            status_code=400, detail="repo and branch are required"
        )

    try:
        return create_branch(repo, branch, base)
    except Exception:
        logger.exception("Operation failed")
        raise HTTPException(
            status_code=500, detail="An internal error occurred"
        )


@app.post("/github/commit")
def github_commit(data: dict):
    repo = data.get("repo")
    branch = data.get("branch")
    message = data.get("message", "Update from Kronos")
    changes = data.get("changes", [])

    if not repo or not branch or not changes:
        raise HTTPException(
            status_code=400, detail="repo, branch, and changes are required"
        )

    try:
        return commit_changes(repo, branch, message, changes)
    except Exception:
        logger.exception("Operation failed")
        raise HTTPException(
            status_code=500, detail="An internal error occurred"
        )


@app.post("/github/open_pr")
def github_open_pr(data: dict):
    repo = data.get("repo")
    title = data.get("title")
    body = data.get("body", "")
    head = data.get("head")
    base = data.get("base", "main")

    if not repo or not title or not head:
        raise HTTPException(
            status_code=400, detail="repo, title, and head are required"
        )

    try:
        return open_pull_request(repo, title, body, head, base)
    except Exception:
        logger.exception("Operation failed")
        raise HTTPException(
            status_code=500, detail="An internal error occurred"
        )


@app.post("/fix_plan")
def fix_plan(data: dict):
    plan = generate_fix_plan(data)
    return apply_fix_plan(plan)


@app.post("/deploy_check")
def deploy_check(data: dict):
    path = data.get("path", ".")
    deployment = deployment_check(path)
    plan = generate_deployment_plan({"deployment": deployment})
    return {
        "deployment": deployment,
        "plan": plan,
    }


@app.post("/deploy/build_check")
def deploy_build_check(data: dict):
    path = data.get("path", ".")
    return build_check(path)


@app.post("/deploy/config")
def deploy_config(data: dict):
    path = data.get("path", ".")
    return deployment_config(path)


@app.post("/deploy/release_approval")
def deploy_release_approval(data: dict):
    return release_approval(data)


@app.get("/github/login")
def github_login(request: Request):
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=500, detail="GITHUB_OAUTH_CLIENT_ID not configured"
        )

    state = str(uuid.uuid4())
    params = {
        "client_id": client_id,
        "scope": "repo user",
        "state": state,
    }
    url = "https://github.com/login/oauth/authorize"
    redirect = url + "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    # store state in server-side session if available, else cookie session
    if SESSION_STORE:
        sid = request.cookies.get("session_id") or SESSION_STORE.new_session()
        sess = SESSION_STORE.get(sid) or {}
        sess["oauth_state"] = state
        SESSION_STORE.set(sid, sess)
        response = RedirectResponse(redirect)
        response.set_cookie(
            "session_id",
            sid,
            httponly=True,
            samesite="lax",
            secure=_SECURE_COOKIES,
        )
        return response
    else:
        request.session["oauth_state"] = state
    return RedirectResponse(redirect)


@app.get("/github/callback")
def github_callback(request: Request, code: str = None, state: str = None):
    # retrieve expected state from session store or cookie
    expected = None
    if SESSION_STORE:
        sid = request.cookies.get("session_id")
        if sid:
            sess = SESSION_STORE.get(sid)
            expected = sess.get("oauth_state")
    else:
        expected = request.session.get("oauth_state")

    if not code or state != expected:
        raise HTTPException(status_code=400, detail="Invalid OAuth callback")

    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500, detail="OAuth client not configured"
        )

    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }
    resp = requests.post(token_url, data=payload, headers=headers)
    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=400, detail="Failed to obtain access token"
        )

    if SESSION_STORE:
        sid = request.cookies.get("session_id") or SESSION_STORE.new_session()
        sess = SESSION_STORE.get(sid) or {}
        sess["github_token"] = access_token
        SESSION_STORE.set(sid, sess)
        response = RedirectResponse("/")
        response.set_cookie(
            "session_id",
            sid,
            httponly=True,
            samesite="lax",
            secure=_SECURE_COOKIES,
        )
        return response
    else:
        request.session["github_token"] = access_token
        return RedirectResponse("/")


@app.post("/github/logout")
def github_logout(request: Request):
    request.session.pop("github_token", None)
    request.session.pop("oauth_state", None)
    return {"status": "logged_out"}


def _worker_run_job(job_id: str, repo_url: str):
    JOBS[job_id]["status"] = "running"
    update_job_status(job_id, "running")
    try:
        report = scan_repository(repo_url)
        # ensure report carries path for fix_agent
        if isinstance(report, dict):
            report["path"] = report.get("path", ".")
        fix_plan = generate_fix_plan(report)
        # generate preview patches
        applied = apply_fix_plan(fix_plan)

        # For demo: produce a single summary change file
        change_content = "Auto-generated fix summary:\n" + str(report)
        changes = [
            {
                "path": f"kronos_fixes/{job_id}.txt",
                "content": change_content,
                "message": "Kronos auto-fix summary",
            }
        ]

        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["report"] = report
        JOBS[job_id]["fix_plan"] = fix_plan
        JOBS[job_id]["applied"] = applied
        JOBS[job_id]["changes"] = changes
        update_job_status(
            job_id,
            "completed",
            {"report": report, "fix_plan": fix_plan, "changes": changes},
        )
    except Exception as exc:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(exc)
        update_job_status(job_id, "failed", {"error": str(exc)})


def _worker_run_files(job_id: str, path: str):
    JOBS[job_id]["status"] = "running"
    try:
        report = analyze_repo(path)
        fix_plan = generate_fix_plan(report)
        applied = apply_fix_plan(fix_plan)

        # For uploads we will create changes for each uploaded file
        changes = []
        for root, _, files in os.walk(path):
            for fn in files:
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, path)
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                changes.append(
                    {
                        "path": rel,
                        "content": content,
                        "message": "Uploaded by user",
                    }
                )

        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["report"] = report
        JOBS[job_id]["fix_plan"] = fix_plan
        JOBS[job_id]["applied"] = applied
        JOBS[job_id]["changes"] = changes
    except Exception as exc:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(exc)


@app.post("/submit_project")
def submit_project(request: Request, data: dict):
    repo_url = data.get("url")
    if not repo_url:
        raise HTTPException(status_code=400, detail="Repository URL required")

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "queued", "repo": repo_url}
    create_job(
        job_id, repo=repo_url, payload={"type": "repo", "url": repo_url}
    )

    thread = threading.Thread(
        target=_worker_run_job, args=(job_id, repo_url), daemon=True
    )
    thread.start()

    return {"job_id": job_id, "status": "queued"}


@app.get("/job_status/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        # try persistent store
        pj = get_job(job_id)
        if pj:
            return pj
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/deploy_confirm")
def deploy_confirm(request: Request, data: dict):
    job_id = data.get("job_id")
    # action = data.get("action", "open_pr")  # reserved for future action routing

    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # retrieve token from session store or cookie
    token = None
    if SESSION_STORE:
        sid = request.cookies.get("session_id")
        if sid:
            token = SESSION_STORE.get(sid).get("github_token")
    else:
        token = request.session.get("github_token")
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Not authenticated with GitHub; please sign in",
        )

    repo_full = data.get("repo") or job.get("repo")
    if not repo_full:
        raise HTTPException(
            status_code=400,
            detail="Repository full name required (owner/repo)",
        )

    branch_name = f"kronos-fix-{job_id[:8]}"

    try:
        create_branch(repo_full, branch_name, token=token)
        commit_resp = commit_changes(
            repo_full,
            branch_name,
            "Kronos automated fixes",
            job.get("changes", []),
            token=token,
        )
        pr = open_pull_request(
            repo_full,
            f"Kronos fixes ({job_id[:8]})",
            "Automated fixes suggested by Kronos.",
            branch_name,
            token=token,
        )

        job["deployed"] = {
            "branch": branch_name,
            "commit": commit_resp,
            "pr": pr,
        }
        return {"status": "deployed", "pr": pr}
    except Exception:
        logger.exception("Operation failed")
        raise HTTPException(
            status_code=500, detail="An internal error occurred"
        )


@app.get("/whoami")
def whoami(request: Request):
    # ensure csrf exists for clients
    ensure_csrf_in_session(request.session)
    token = request.session.get("github_token")
    if not token:
        return {
            "authenticated": False,
            "csrf_token": request.session.get("csrf_token"),
        }
    try:
        gh = Github(token)
        user = gh.get_user()
        return {
            "authenticated": True,
            "login": user.login,
            "name": getattr(user, "name", None),
            "avatar_url": getattr(user, "avatar_url", None),
            "csrf_token": request.session.get("csrf_token"),
        }
    except Exception:
        return {
            "authenticated": False,
            "csrf_token": request.session.get("csrf_token"),
        }


@app.post("/upload_files")
def upload_files(
    request: Request,
    files: List[UploadFile] = File(None),
    text: str = Form(None),
):
    if not files and not text:
        raise HTTPException(
            status_code=400, detail="No files or text provided"
        )

    job_id = str(uuid.uuid4())
    upload_dir = os.path.join("/workspaces/Kronos-Vibe-Coder/uploads", job_id)
    os.makedirs(upload_dir, exist_ok=True)

    # Enforce upload limits
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB per file
    MAX_TOTAL = 10 * 1024 * 1024  # 10 MB total
    total = 0

    def _sanitize_name(name: str) -> str:
        keep = []
        for ch in name:
            if ch.isalnum() or ch in "._-":
                keep.append(ch)
        return "".join(keep) or "file"

    if files:
        for up in files:
            content = up.file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, detail=f"File too large: {up.filename}"
                )
            total += len(content)
            if total > MAX_TOTAL:
                raise HTTPException(
                    status_code=400, detail="Total upload size exceeded"
                )
            fname = _sanitize_name(up.filename)
            dest = os.path.join(upload_dir, fname)
            with open(dest, "wb") as f:
                f.write(content)

    if text:
        # Save as a single file
        with open(
            os.path.join(upload_dir, "chat_input.txt"), "w", encoding="utf-8"
        ) as f:
            f.write(text)

    JOBS[job_id] = {"status": "queued", "upload_dir": upload_dir}
    create_job(job_id, upload_dir=upload_dir, payload={"type": "upload"})
    update_job_status(job_id, "queued")
    thread = threading.Thread(
        target=_worker_run_files, args=(job_id, upload_dir), daemon=True
    )
    thread.start()
    return {"job_id": job_id, "status": "queued"}
