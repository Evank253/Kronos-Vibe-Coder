from pathlib import Path


def security_scan(path="."):
    findings = []
    path = Path(path)

    if (path / ".env").exists():
        findings.append("Environment file detected. Check secrets.")

    return {
        "security_findings": findings,
        "status": "scanned"
    }
