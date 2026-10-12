"""
Real fix agent – generates and applies actual file changes.

Capabilities:
- Normalize whitespace (tabs → spaces, strip trailing, ensure EOF newline)
- Python AST syntax validation (flag files that fail to parse)
- Safe rewrite: bare `except:` → `except Exception:`
- Unified diffs for preview; real writes when target_root is set
"""
from __future__ import annotations

from datetime import datetime, timezone
import ast
import difflib
import os
import re
from typing import Any, Dict, List, Optional, Set

_SKIP_DIR_NAMES: Set[str] = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", "coverage",
}


def _should_skip_dir(dirpath: str) -> bool:
    parts = set(os.path.normpath(dirpath).split(os.sep))
    return bool(parts & _SKIP_DIR_NAMES)


def _normalize_text(s: str) -> str:
    if s == "":
        return s
    lines = s.splitlines()
    new_lines = [line.replace("\t", "    ").rstrip() for line in lines]
    text = "\n".join(new_lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def _fix_bare_except(s: str) -> str:
    return re.sub(r"(?m)^(\s*)except\s*:\s*$", r"\1except Exception:", s)


def _python_syntax_ok(s: str) -> bool:
    try:
        ast.parse(s)
        return True
    except SyntaxError:
        return False


def _apply_safe_python_fixes(orig: str) -> tuple[str, List[str]]:
    tags: List[str] = []
    new = _normalize_text(orig)
    if new != orig:
        tags.append("whitespace_normalize")

    fixed_except = _fix_bare_except(new)
    if fixed_except != new:
        tags.append("bare_except")
        new = fixed_except

    # Keep only if we did not break previously valid Python
    if _python_syntax_ok(orig) and not _python_syntax_ok(new):
        return orig, []
    return new, tags


def generate_fix_plan_for_path(root_path: str, *, include_syntax_errors: bool = True) -> Dict[str, Any]:
    fixes: List[Dict[str, Any]] = []
    syntax_errors: List[Dict[str, str]] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        if _should_skip_dir(dirpath):
            continue
        for fn in filenames:
            if not fn.endswith((".py", ".md", ".txt", ".cfg", ".ini", ".yml", ".yaml")):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    orig = f.read()
            except OSError:
                continue

            rel = os.path.relpath(fp, root_path)

            if fn.endswith(".py"):
                if include_syntax_errors and not _python_syntax_ok(orig):
                    syntax_errors.append({"path": rel, "issue": "syntax_error"})
                new, tags = _apply_safe_python_fixes(orig)
            else:
                new = _normalize_text(orig)
                tags = ["whitespace_normalize"] if new != orig else []

            if new != orig:
                fixes.append({
                    "path": rel,
                    "original": orig,
                    "updated": new,
                    "tags": tags,
                })

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "fix_count": len(fixes),
        "fixes": fixes,
        "syntax_errors": syntax_errors,
        "status": "plan_created",
    }


def generate_fix_plan(review_or_path) -> Dict[str, Any]:
    if isinstance(review_or_path, dict):
        path = review_or_path.get("path") or review_or_path.get("repo_path") or "."
        return generate_fix_plan_for_path(path)
    if isinstance(review_or_path, str):
        return generate_fix_plan_for_path(review_or_path)
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "fix_count": 0,
        "fixes": [],
        "syntax_errors": [],
        "status": "no_action",
    }


def apply_fix_plan(fix_plan: Dict[str, Any], target_root: Optional[str] = None) -> Dict[str, Any]:
    applied = []
    for item in fix_plan.get("fixes", []):
        path = item["path"]
        updated = item["updated"]
        if target_root:
            dest = os.path.join(target_root, path)
            parent = os.path.dirname(dest)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(updated)
            applied.append({
                "path": path,
                "action": "written",
                "tags": item.get("tags", []),
            })
        else:
            orig = item.get("original", "").splitlines(keepends=True)
            new = updated.splitlines(keepends=True)
            diff = "".join(difflib.unified_diff(orig, new, fromfile="a/" + path, tofile="b/" + path))
            applied.append({"path": path, "patch": diff, "tags": item.get("tags", [])})

    return {
        "status": "applied" if target_root else "preview",
        "changes": applied,
        "fix_count": len(applied),
    }


def fixes_to_commit_changes(fix_plan: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {
            "path": item["path"],
            "content": item["updated"],
            "message": f"fix: {', '.join(item.get('tags') or ['auto'])} in {item['path']}",
        }
        for item in fix_plan.get("fixes", [])
    ]
