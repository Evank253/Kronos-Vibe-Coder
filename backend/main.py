import subprocess

from fastapi import FastAPI, HTTPException
from backend.agents.repo_analyzer import analyze_repo
from backend.agents.debug_agent import debug_project
from backend.github.github_manager import clone_repository

app = FastAPI(title="Kronos Vibe Coder")

@app.get("/")
def home():
    return {
        "name": "Kronos Vibe Coder",
        "status": "online"
    }

@app.post("/analyze")
def analyze(data: dict):
    repo = data.get("repo", ".")
    return analyze_repo(repo)

@app.post("/debug")
def debug(data: dict):
    return debug_project(data)

@app.post("/scan_repo")
def scan_repo(data: dict):
    repo_url = data.get("url")
    if not repo_url:
        raise HTTPException(status_code=400, detail="Repository URL required")

    try:
        return clone_repository(repo_url)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
