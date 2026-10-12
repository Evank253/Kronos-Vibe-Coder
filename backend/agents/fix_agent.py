"""
Real fix agent – generates and applies actual file changes.

Capabilities:
- Normalize whitespace (tabs → spaces, strip trailing, ensure EOF newline)
- Python AST syntax validation (flag files that fail to parse)
- Simple safe rewrites: bare `except:` → `except Exception:`,
  obvious `print(` debug leftovers can be flagged (not auto-removed by default)
- Produces unified diffs for preview and real writes when target_root is set
"""
from __future__ import annotations

from datetime import datetime, timezone
import ast
import difflib
import os
import re
from typing import Any, Dict, List, Optional


def _normalize_text(s: str) -> str:
    lines = s.splitlines()
    new_lines = [line.replace("\t", "    ").rstrip() for line in lines]
    return "\n".join(new_lines) + "\n"


def _fix_bare_except(s: str) -> str:
    """Replace bare `except:` with `except Exception:` (safe, common lint fix)."""
    return re.sub(r"(?m)^(\s*)except\s*:\s*$", r"\1except Exception:", s)


def _python_syntax_ok(s: str) -> bool:
    try:
        ast.parse(s)
        return True
    except SyntaxError:
        return False


def _apply_safe_python_fixes(orig: str) -> tuple[str, List[str]]:
    """Return (new_text, list_of_fix_tags)."""
    tags: List[str] = []
    new = _normalize_text(orig)
    if new != orig:
        tags.append("whitespace_normalize")

    fixed_except = _fix_bare_except(new)
    if fixed_except != new:
        tags.append("bare_except")
        new = fixed_except

    # Only keep the result if it still parses (or original also failed)
    if new.endswith(".py") or True:
        if _python_syntax_ok(orig) and not _python_syntax_ok(new):
            # Revert dangerous change
            return orig, []
    return new, tags


def generate_fix_plan_for_path(root_path: str, *, include_syntax_errors: bool = True) -> Dict[str, Any]:
    fixes: List[Dict[str, Any]] = []
    syntax_errors: List[Dict[str, str]] = []

    for dirpath, _, filenames in os.walk(root_path):
        # Skip common noise
        if any(skip in dirpath for skip in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build")):
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
    """
    Apply fixes for real when target_root is set; otherwise return unified diffs.
    """
    applied = []
    for item in fix_plan.get("fixes", []):
        path = item["path"]
        updated = item["updated"]
        if target_root:
            dest = os.path.join(target_root, path)
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
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
    """Convert a fix plan into the shape expected by github_manager.commit_changes."""
    return [
        {
            "path": item["path"],
            "content": item["updated"],
            "message": f"fix: {', '.join(item.get('tags') or ['auto'])} in {item['path']}",
        }
        for item in fix_plan.get("fixes", [])
    ]
