from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from backend.csrf import CSRFMiddleware, ensure_csrf_in_session
from backend.codespace_adapter import static_root
import os
import logging
from backend.session_store import get_session_store
import threading
import uuid
import requests
from github import Github
from typing import List, Optional

from backend.agents.repo_analyzer import analyze_repo
from backend.agents.debug_agent import debug_project
from backend.agents.scan_pipeline import scan_repository
from backend.agents.deploy_agent import deployment_check, generate_deployment_plan
from backend.agents.deployment_manager import build_check, deployment_config, release_approval
from backend.agents.fix_agent import generate_fix_plan, apply_fix_plan, fixes_to_commit_changes
from backend.jobs import init_db, create_job, update_job_status, get_job
from backend.agents.github_manager import create_branch, commit_changes, open_pull_request
from backend.vibe_endpoints import router as vibe_router

app = FastAPI(title="Kronos Vibe Coder")

SECRET_KEY = os.getenv("SESSION_SECRET", "dev-secret-key")
app.add_middleware(CSRFMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

STATIC_DIR = static_root()
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(vibe_router)

JOBS = {}
init_db()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("kronos")

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(SENTRY_DSN)
        logger.info("Sentry initialized")
    except Exception:
        logger.exception("Failed to initialize Sentry")

SESSION_STORE = get_session_store()
logger.info("Session store: %s", type(SESSION_STORE).__name__)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    index_path = STATIC_DIR / "index.html"
    try:
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    except OSError:
        return {"name": "Kronos Vibe Coder", "status": "online"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(data: dict):
    return analyze_repo(data.get("repo", "."))


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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/github/create_branch")
def github_create_branch(data: dict):
    repo = data.get("repo")
    branch = data.get("branch")
    base = data.get("base", "main")
    if not repo or not branch:
        raise HTTPException(status_code=400, detail="repo and branch are required")
    try:
        return create_branch(repo, branch, base)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/github/commit")
def github_commit(data: dict):
    repo = data.get("repo")
    branch = data.get("branch")
    message = data.get("message", "Update from Kronos")
    changes = data.get("changes", [])
    if not repo or not branch or not changes:
        raise HTTPException(status_code=400, detail="repo, branch, and changes are required")
    try:
        return commit_changes(repo, branch, message, changes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/github/open_pr")
def github_open_pr(data: dict):
    repo = data.get("repo")
    title = data.get("title")
    body = data.get("body", "")
    head = data.get("head")
    base = data.get("base", "main")
    if not repo or not title or not head:
        raise HTTPException(status_code=400, detail="repo, title, and head are required")
    try:
        return open_pull_request(repo, title, body, head, base)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/fix_plan")
def fix_plan(data: dict):
    plan = generate_fix_plan(data)
    return apply_fix_plan(plan)


@app.post("/deploy_check")
def deploy_check(data: dict):
    path = data.get("path", ".")
    deployment = deployment_check(path)
    plan = generate_deployment_plan({"deployment": deployment})
    return {"deployment": deployment, "plan": plan}


@app.post("/deploy/build_check")
def deploy_build_check(data: dict):
    return build_check(data.get("path", "."))


@app.post("/deploy/config")
def deploy_config(data: dict):
    return deployment_config(data.get("path", "."))


@app.post("/deploy/release_approval")
def deploy_release_approval(data: dict):
    return release_approval(data)


@app.get("/github/login")
def github_login(request: Request):
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GITHUB_OAUTH_CLIENT_ID not configured")

    state = str(uuid.uuid4())
    params = {"client_id": client_id, "scope": "repo user", "state": state}
    redirect = "https://github.com/login/oauth/authorize?" + "&".join(
        f"{k}={v}" for k, v in params.items()
    )

    sid = request.cookies.get("session_id") or SESSION_STORE.new_session()
    sess = SESSION_STORE.get(sid) or {}
    sess["oauth_state"] = state
    SESSION_STORE.set(sid, sess)
    response = RedirectResponse(redirect)
    response.set_cookie("session_id", sid, httponly=True)
    request.session["oauth_state"] = state
    return response


@app.get("/github/callback")
def github_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    expected = request.session.get("oauth_state")
    sid = request.cookies.get("session_id")
    if sid:
        expected = (SESSION_STORE.get(sid) or {}).get("oauth_state") or expected

    if not code or state != expected:
        raise HTTPException(status_code=400, detail="Invalid OAuth callback")

    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="OAuth client not configured")

    resp = requests.post(
        "https://github.com/login/oauth/access_token",
        data={"client_id": client_id, "client_secret": client_secret, "code": code},
        headers={"Accept": "application/json"},
    )
    access_token = resp.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to obtain access token")

    sid = request.cookies.get("session_id") or SESSION_STORE.new_session()
    sess = SESSION_STORE.get(sid) or {}
    sess["github_token"] = access_token
    SESSION_STORE.set(sid, sess)
    request.session["github_token"] = access_token
    response = RedirectResponse("/")
    response.set_cookie("session_id", sid, httponly=True)
    return response


@app.post("/github/logout")
def github_logout(request: Request):
    request.session.pop("github_token", None)
    request.session.pop("oauth_state", None)
    sid = request.cookies.get("session_id")
    if sid:
        sess = SESSION_STORE.get(sid) or {}
        sess.pop("github_token", None)
        sess.pop("oauth_state", None)
        SESSION_STORE.set(sid, sess)
    return {"status": "logged_out"}


def _worker_run_job(job_id: str, repo_url: str):
    JOBS[job_id]["status"] = "running"
    update_job_status(job_id, "running")
    try:
        report = scan_repository(repo_url)
        if isinstance(report, dict) and report.get("status") == "error":
            raise RuntimeError(report.get("error") or "scan failed")

        path = "."
        if isinstance(report, dict):
            path = report.get("path") or (report.get("repository") or {}).get("path") or "."

        fix_plan = generate_fix_plan(path)
        applied = apply_fix_plan(fix_plan)
        changes = fixes_to_commit_changes(fix_plan)
        if not changes:
            changes = [{
                "path": f"kronos_fixes/{job_id[:8]}_no_auto_fixes.md",
                "content": (
                    "# Kronos scan complete\n\nNo auto-applicable fixes.\n"
                    f"Syntax errors noted: {len(fix_plan.get('syntax_errors') or [])}\n"
                ),
                "message": "Kronos scan – no auto fixes",
            }]

        JOBS[job_id].update({
            "status": "completed",
            "report": report,
            "path": path,
            "fix_plan": fix_plan,
            "applied": applied,
            "changes": changes,
        })
        update_job_status(job_id, "completed", {
            "fix_count": fix_plan.get("fix_count"),
            "syntax_errors": fix_plan.get("syntax_errors"),
            "change_count": len(changes),
        })
    except Exception as exc:
        logger.exception("job %s failed", job_id)
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(exc)
        update_job_status(job_id, "failed", {"error": str(exc)})


def _worker_run_files(job_id: str, path: str):
    JOBS[job_id]["status"] = "running"
    try:
        report = analyze_repo(path)
        report["path"] = path
        fix_plan = generate_fix_plan(path)
        applied = apply_fix_plan(fix_plan, target_root=path)
        changes = fixes_to_commit_changes(fix_plan)
        JOBS[job_id].update({
            "status": "completed",
            "report": report,
            "path": path,
            "fix_plan": fix_plan,
            "applied": applied,
            "changes": changes,
        })
        update_job_status(job_id, "completed", {
            "fix_count": fix_plan.get("fix_count"),
            "change_count": len(changes),
        })
    except Exception as exc:
        logger.exception("upload job %s failed", job_id)
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(exc)
        update_job_status(job_id, "failed", {"error": str(exc)})


@app.post("/submit_project")
def submit_project(request: Request, data: dict):
    repo_url = data.get("url")
    if not repo_url:
        raise HTTPException(status_code=400, detail="Repository URL required")
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "queued", "repo": repo_url}
    create_job(job_id, repo=repo_url, payload={"type": "repo", "url": repo_url})
    threading.Thread(target=_worker_run_job, args=(job_id, repo_url), daemon=True).start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/job_status/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if job:
        return job
    pj = get_job(job_id)
    if pj:
        return pj
    raise HTTPException(status_code=404, detail="Job not found")


@app.post("/deploy_confirm")
def deploy_confirm(request: Request, data: dict):
    job_id = data.get("job_id")
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    token = request.session.get("github_token")
    sid = request.cookies.get("session_id")
    if not token and sid:
        token = (SESSION_STORE.get(sid) or {}).get("github_token")
    if not token:
        raise HTTPException(status_code=403, detail="Not authenticated with GitHub; please sign in")

    repo_full = data.get("repo")
    if not repo_full or "/" not in str(repo_full):
        raise HTTPException(status_code=400, detail="Repository full name required (owner/repo)")

    changes = job.get("changes") or []
    if not changes:
        raise HTTPException(status_code=400, detail="No changes to commit for this job")

    branch_name = f"kronos-fix-{job_id[:8]}"
    base = data.get("base", "main")
    fix_count = (job.get("fix_plan") or {}).get("fix_count", len(changes))

    try:
        create_branch(repo_full, branch_name, base_branch=base, token=token)
        commit_resp = commit_changes(
            repo_full,
            branch_name,
            f"Kronos automated fixes ({fix_count} files)",
            changes,
            token=token,
        )
        pr = open_pull_request(
            repo_full,
            f"Kronos fixes ({job_id[:8]})",
            "Automated fixes from Kronos-Vibe-Coder. Review carefully before merge.",
            branch_name,
            base=base,
            token=token,
        )
        job["deployed"] = {"branch": branch_name, "commit": commit_resp, "pr": pr}
        return {"status": "deployed", "pr": pr}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/whoami")
def whoami(request: Request):
    ensure_csrf_in_session(request.session)
    token = request.session.get("github_token")
    sid = request.cookies.get("session_id")
    if not token and sid:
        token = (SESSION_STORE.get(sid) or {}).get("github_token")
    if not token:
        return {"authenticated": False, "csrf_token": request.session.get("csrf_token")}
    try:
        user = Github(token).get_user()
        return {
            "authenticated": True,
            "login": user.login,
            "name": getattr(user, "name", None),
            "avatar_url": getattr(user, "avatar_url", None),
            "csrf_token": request.session.get("csrf_token"),
        }
    except Exception:
        return {"authenticated": False, "csrf_token": request.session.get("csrf_token")}


@app.post("/upload_files")
def upload_files(
    request: Request,
    files: Optional[List[UploadFile]] = File(None),
    text: Optional[str] = Form(None),
):
    if not files and not text:
        raise HTTPException(status_code=400, detail="No files or text provided")

    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(os.getcwd(), "uploads", job_id)
    os.makedirs(upload_dir, exist_ok=True)

    max_file = 2 * 1024 * 1024
    max_total = 10 * 1024 * 1024
    total = 0

    def _sanitize(name: str) -> str:
        keep = [ch for ch in (name or "file") if ch.isalnum() or ch in "._-"]
        return "".join(keep) or "file"

    if files:
        for up in files:
            content = up.file.read()
            if len(content) > max_file:
                raise HTTPException(status_code=400, detail=f"File too large: {up.filename}")
            total += len(content)
            if total > max_total:
                raise HTTPException(status_code=400, detail="Total upload size exceeded")
            with open(os.path.join(upload_dir, _sanitize(up.filename)), "wb") as f:
                f.write(content)

    if text:
        with open(os.path.join(upload_dir, "chat_input.txt"), "w", encoding="utf-8") as f:
            f.write(text)

    JOBS[job_id] = {"status": "queued", "upload_dir": upload_dir}
    create_job(job_id, upload_dir=upload_dir, payload={"type": "upload"})
    update_job_status(job_id, "queued")
    threading.Thread(target=_worker_run_files, args=(job_id, upload_dir), daemon=True).start()
    return {"job_id": job_id, "status": "queued"}
