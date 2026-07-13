from pathlib import Path


def build_check(path="."):
    path = Path(path)
    checks = {
        "dockerfile": (path / "Dockerfile").exists(),
        "docker_compose": (path / "docker-compose.yml").exists(),
        "package_json": (path / "package.json").exists(),
        "requirements": (path / "requirements.txt").exists(),
        "github_actions": (path / ".github/workflows").exists(),
    }
    score = sum(checks.values())
    return {
        "deployment_checks": checks,
        "deployment_score": f"{score}/{len(checks)}",
        "build_ready": score >= 3,
    }


def deployment_config(path="."):
    path = Path(path)
    files = {
        "Dockerfile": (path / "Dockerfile").exists(),
        "docker_compose": (path / "docker-compose.yml").exists(),
        "github_actions": (path / ".github/workflows").exists(),
    }
    required = [name for name, exists in files.items() if not exists]
    return {
        "deployment_files": files,
        "missing_files": required,
        "ready": len(required) == 0,
    }


def release_approval(report):
    if report.get("deployment_checks", {}).get("build_ready"):
        return {
            "status": "approved",
            "message": "Deployment release may proceed.",
        }

    return {
        "status": "requires_approval",
        "message": "Complete the deployment configuration before release.",
    }
