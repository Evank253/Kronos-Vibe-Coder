import subprocess
from pathlib import Path


def clone_repository(repo_url: str):
    workspace = Path("workspace")
    workspace.mkdir(exist_ok=True)

    repo_name = repo_url.rstrip("/").split("/")[-1]
    destination = workspace / repo_name

    if destination.exists():
        return {
            "status": "already_exists",
            "path": str(destination)
        }

    subprocess.run(
        ["git", "clone", repo_url, str(destination)],
        check=True
    )

    return {
        "status": "cloned",
        "repository": repo_name,
        "path": str(destination)
    }
