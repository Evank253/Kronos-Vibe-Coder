"""Clone repositories into a local workspace."""
from __future__ import annotations

import subprocess
from pathlib import Path


def clone_repo(url: str, workspace: str = "workspace") -> dict:
    root = Path(workspace)
    root.mkdir(exist_ok=True)

    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    path = root / name

    if path.exists():
        return {"status": "exists", "path": str(path), "repository": name}

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return {
            "status": "error",
            "repository": name,
            "path": str(path),
            "error": (exc.stderr or exc.stdout or str(exc)).strip(),
        }

    return {"status": "cloned", "repository": name, "path": str(path)}
