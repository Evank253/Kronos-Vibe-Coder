"""Count and sample files in a repository, skipping noise directories."""
from __future__ import annotations

from pathlib import Path

_SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def analyze_repo(path) -> dict:
    root = Path(path)
    files = []
    if not root.exists():
        return {"status": "path_not_found", "files_found": 0, "files": []}

    for item in root.rglob("*"):
        if not item.is_file():
            continue
        if any(part in _SKIP for part in item.parts):
            continue
        files.append(str(item))

    return {
        "status": "analysis complete",
        "files_found": len(files),
        "files": files[:100],
    }
