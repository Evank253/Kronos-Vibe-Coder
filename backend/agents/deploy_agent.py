from pathlib import Path


def deployment_check(path="."):
    path = Path(path)
    checks = {
        "dockerfile": (path / "Dockerfile").exists(),
        "docker_compose": (path / "docker-compose.yml").exists(),
        "requirements": (path / "requirements.txt").exists(),
        "package_json": (path / "package.json").exists(),
        "github_actions": (path / ".github/workflows").exists(),
    }
    score = sum(checks.values())

    return {
        "deployment_score": f"{score}/{len(checks)}",
        "checks": checks,
        "ready": score >= 3,
    }


def generate_deployment_plan(report):
    deployment = report.get("deployment", {})
    steps = []

    if not deployment.get("checks", {}).get("dockerfile"):
        steps.append("Create Dockerfile")

    if not deployment.get("checks", {}).get("github_actions"):
        steps.append("Create GitHub Actions workflow")

    if not steps:
        steps.append("Deployment configuration looks ready")

    return {
        "status": "plan_generated",
        "steps": steps
    }
