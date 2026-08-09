"""
Kronos-Vibe-Coder <-> Vibe Developer bridge client.

Vibe Developer publishes a dependency contract (pinned package versions) at
POST /api/vibe/developer. Kronos-Vibe-Coder is the "Coder" side of that
contract: it must wait for the Developer to publish, align its own
dependency file to the published pins, and only then acknowledge and run.

Order enforced by the Developer's bridge (see vibe-developer/server/services/
vibeBridge.js): developer -> coder -> smoke -> deploy. This module is the
Coder half of that handshake.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_DEVELOPER_URL = "http://localhost:4000"


def developer_url() -> str:
    return os.getenv("VIBE_DEVELOPER_URL", DEFAULT_DEVELOPER_URL).rstrip("/")


class DeveloperNotReadyError(RuntimeError):
    """Raised when the Coder tries to proceed before the Developer publishes pins."""


def get_brief(base_url: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    """Fetch what the Coder should build against. Never raises on a 'not ready' brief."""
    url = f"{base_url or developer_url()}/api/vibe/coder/brief"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def wait_for_developer(
    base_url: str | None = None,
    timeout_seconds: float = 120.0,
    poll_seconds: float = 2.0,
) -> dict[str, Any]:
    """
    Block until Vibe Developer has published its pins (stage == developer_done),
    or raise DeveloperNotReadyError after timeout_seconds.

    This is the ordering guarantee: Coder cannot proceed until Developer runs first.
    """
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            brief = get_brief(base_url)
            if brief.get("ready"):
                return brief
        except requests.RequestException as exc:  # Developer server not up yet
            last_error = exc
        time.sleep(poll_seconds)
    raise DeveloperNotReadyError(
        f"Vibe Developer did not publish a dependency contract within "
        f"{timeout_seconds}s at {base_url or developer_url()}"
        f"{f' (last error: {last_error})' if last_error else ''}"
    )


_PIN_LINE_RE_TEMPLATE = r"^(?P<pkg>{pkg})(?P<extras>\[[^\]]*\])?\s*(==|>=|<=|~=|>|<)?\s*(?P<version>[\w.\-]*)?\s*$"


def align_requirements(
    pins: dict[str, str],
    requirements_path: str | Path = "requirements.txt",
) -> list[str]:
    """
    Rewrite lines in requirements_path for any package named in `pins` to an
    exact `package==version` pin matching the Developer's contract. Packages
    not present in `pins` are left untouched. Packages in `pins` that aren't
    already listed are appended.

    Returns the list of "pkg==version" lines that were changed or added.
    """
    path = Path(requirements_path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    changed: list[str] = []
    remaining_pins = dict(pins)
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        matched_pkg = None
        for pkg in remaining_pins:
            pattern = _PIN_LINE_RE_TEMPLATE.format(pkg=re.escape(pkg))
            if re.match(pattern, stripped, flags=re.IGNORECASE):
                matched_pkg = pkg
                break

        if matched_pkg is None:
            new_lines.append(line)
            continue

        pinned = f"{matched_pkg}=={remaining_pins.pop(matched_pkg)}"
        if pinned != stripped:
            changed.append(pinned)
        new_lines.append(pinned)

    # Any pins for packages not already in requirements.txt get appended.
    for pkg, version in remaining_pins.items():
        pinned = f"{pkg}=={version}"
        new_lines.append(pinned)
        changed.append(pinned)

    if changed:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return changed


def acknowledge_coder(
    implemented: list[str],
    blockers: list[str] | None = None,
    base_url: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    url = f"{base_url or developer_url()}/api/vibe/coder"
    resp = requests.post(
        url,
        json={"implemented": implemented, "blockers": blockers or []},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def report_smoke(
    ok: bool,
    detail: str = "",
    base_url: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    url = f"{base_url or developer_url()}/api/vibe/smoke"
    resp = requests.post(url, json={"ok": ok, "detail": detail}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
