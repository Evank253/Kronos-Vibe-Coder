"""Environment capture for reproducibility metadata."""
import os
import platform
import shutil
import subprocess
from typing import Dict


def _version(command):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        return (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr) else "unknown"
    except Exception:
        return "unavailable"


def capture_environment() -> Dict[str, str]:
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "git": _version(["git", "--version"]),
        "pytest": _version(["python", "-m", "pytest", "--version"]),
        "cwd": os.getcwd(),
        "executable": shutil.which("python") or "unknown",
    }
