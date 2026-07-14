from __future__ import annotations

import os
from pathlib import Path


_BLOCKED_ROOTS = {
    Path("/etc"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
    Path("/run"),
    Path("/boot"),
}


def is_codespace() -> bool:
    return os.getenv("CODESPACES", "").lower() == "true" or bool(
        os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    )


def workspace_root() -> Path:
    env_root = os.getenv("GITHUB_WORKSPACE")
    if env_root:
        return Path(env_root).resolve()

    current = Path(__file__).resolve().parents[1]
    if current.as_posix().startswith("/workspaces/"):
        return current

    return Path.cwd().resolve()


def static_root() -> Path:
    return workspace_root() / "static"


def default_dashboard_path() -> Path:
    return static_root() / "vibe-3d.html"


def resolve_workspace_path(raw_path: str | os.PathLike[str] | None) -> Path:
    requested = Path(str(raw_path or "."))
    if requested.is_absolute():
        raise ValueError("Path must be relative to the workspace root")
    candidate = (workspace_root() / requested).resolve()
    for blocked in _BLOCKED_ROOTS:
        try:
            candidate.relative_to(blocked)
        except ValueError:
            continue
        raise ValueError(f"Path '{candidate}' is not allowed")

    allowed_roots = [workspace_root()]
    if is_codespace():
        workspaces = Path("/workspaces")
        if workspaces.exists():
            allowed_roots.append(workspaces.resolve())

    for root in allowed_roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue

    raise ValueError(f"Path '{candidate}' must stay within the workspace or /tmp")


def dashboard_url(task_id: str | None = None) -> str:
    suffix = f"?task_id={task_id}" if task_id else ""
    return f"/static/vibe-3d.html{suffix}"
