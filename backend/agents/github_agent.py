import subprocess
from pathlib import Path


def clone_repo(url: str):
    workspace = Path("workspace")
    workspace.mkdir(exist_ok=True)

    name = url.rstrip("/").split("/")[-1]
    path = workspace / name

    if path.exists():
        return {"status": "exists", "path": str(path)}

    subprocess.run(["git", "clone", url, str(path)], check=True)

    return {"status": "cloned", "repository": name, "path": str(path)}
