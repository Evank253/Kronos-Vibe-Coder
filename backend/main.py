from fastapi import FastAPI
from backend.agents.repo_analyzer import analyze_repo
from backend.agents.debug_agent import debug_project

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
