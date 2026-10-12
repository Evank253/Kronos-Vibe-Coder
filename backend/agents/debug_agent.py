"""Lightweight debug scan – surfaces real issues found on disk."""
from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any, Dict, List

_SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def debug_project(data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = data or {}
    repo = data.get("repo") or data.get("path") or "."
    root = Path(repo)
    issues: List[Dict[str, str]] = []

    if not root.exists():
        return {
            "status": "debug scan complete",
            "issues_found": [{"path": str(root), "issue": "path_not_found"}],
            "message": f"Path does not exist: {root}",
        }

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            fp = Path(dirpath) / fn
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                issues.append({"path": str(fp.relative_to(root)), "issue": f"read_error: {exc}"})
                continue
            try:
                ast.parse(text)
            except SyntaxError as exc:
                issues.append({
                    "path": str(fp.relative_to(root)),
                    "issue": f"syntax_error: line {exc.lineno}: {exc.msg}",
                })

    return {
        "status": "debug scan complete",
        "issues_found": issues,
        "message": f"Found {len(issues)} issue(s)" if issues else "No errors detected",
    }
