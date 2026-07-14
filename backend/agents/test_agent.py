import subprocess
from pathlib import Path


def run_tests(path="."):
    path = Path(path)
    results = {"tests": "not detected", "build": "not tested"}

    try:
        result = subprocess.run(
            ["python", "-m", "pytest"],
            cwd=str(path),
            capture_output=True,
            text=True,
        )

        results["tests"] = "passed" if result.returncode == 0 else "failed"
        results["output"] = (result.stdout or "") + (
            "\n" + result.stderr if result.stderr else ""
        )
    except Exception as exc:
        results["tests"] = str(exc)

    return results
