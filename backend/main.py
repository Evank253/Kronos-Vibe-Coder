from fastapi import FastAPI, HTTPException
from backend.agents.repo_analyzer import analyze_repo
from backend.agents.debug_agent import debug_project
from backend.agents.report_agent import create_report

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
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing repository URL")

    try:
        return create_report(url)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
