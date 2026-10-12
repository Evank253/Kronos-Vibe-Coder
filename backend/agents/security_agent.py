"""Basic security scan – env files and obvious secret patterns."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

_SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]"), "possible_hardcoded_secret"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "possible_aws_access_key"),
    (re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"), "private_key_material"),
]

_SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def security_scan(path: str = ".") -> dict:
    root = Path(path)
    findings: List[str] = []

    if (root / ".env").exists():
        findings.append("Environment file (.env) detected — ensure secrets are not committed.")

    if not root.exists():
        return {"security_findings": ["path_not_found"], "status": "error"}

    for item in root.rglob("*"):
        if not item.is_file():
            continue
        if any(part in _SKIP for part in item.parts):
            continue
        if item.suffix.lower() not in {".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json", ".sh"}:
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, label in _SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(f"{label} in {item.relative_to(root)}")

    return {"security_findings": findings, "status": "scanned"}
