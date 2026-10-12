"""Run pytest in a project path with a timeout."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def run_tests(path: str = ".", timeout: int = 120) -> dict:
    root = Path(path)
    results = {"tests": "not detected", "build": "not tested"}

    if shutil.which("pytest") is None and shutil.which("python") is None:
        results["tests"] = "pytest_not_available"
        return results

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "-q", "--tb=no"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        results["tests"] = "passed" if result.returncode == 0 else "failed"
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        results["output"] = (out + ("\n" + err if err else "")).strip()
        results["returncode"] = result.returncode
    except subprocess.TimeoutExpired:
        results["tests"] = "timeout"
        results["output"] = f"pytest exceeded {timeout}s"
    except Exception as exc:
        results["tests"] = "error"
        results["output"] = str(exc)

    return results
