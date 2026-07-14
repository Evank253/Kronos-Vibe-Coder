import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backend.agents.repo_analyzer import analyze_repo
from backend.agents.debug_agent import debug_project


def clone_repository(repo_url):
    repo_name = repo_url.rstrip("/").split("/")[-1]
    clone_path = Path(tempfile.mkdtemp(prefix="kronos_repo_")) / repo_name

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(clone_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(clone_path.parent, ignore_errors=True)
        raise RuntimeError(exc.stderr.strip() or exc.stdout.strip())

    return clone_path


def generate_report(data):
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "kronos_report": data,
        "status": "complete",
    }


def detect_languages(path: Path):
    extensions = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".vue": "Vue.js",
        ".html": "HTML",
        ".css": "CSS",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
    }

    found = set()
    for file_path in path.rglob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in extensions:
                found.add(extensions[ext])

    return sorted(found)


def detect_frameworks(path: Path):
    frameworks = set()
    package_json = path / "package.json"

    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }
            if "next" in deps:
                frameworks.add("Next.js")
            if "react" in deps:
                frameworks.add("React")
            if "vue" in deps:
                frameworks.add("Vue.js")
            if "svelte" in deps:
                frameworks.add("Svelte")
            if "fastapi" in deps:
                frameworks.add("FastAPI")
            if "flask" in deps:
                frameworks.add("Flask")
        except json.JSONDecodeError:
            pass

    requirements = path / "requirements.txt"
    pyproject = path / "pyproject.toml"
    if requirements.exists() or pyproject.exists() or any(path.rglob("*.py")):
        try:
            requirements_text = (
                requirements.read_text() if requirements.exists() else ""
            )
            pyproject_text = (
                pyproject.read_text() if pyproject.exists() else ""
            )
            combined = requirements_text + "\n" + pyproject_text
            if "fastapi" in combined:
                frameworks.add("FastAPI")
            if "django" in combined:
                frameworks.add("Django")
            if "flask" in combined:
                frameworks.add("Flask")
        except OSError:
            pass

    if not frameworks:
        if (
            (path / "package-lock.json").exists()
            or (path / "yarn.lock").exists()
            or (path / "pnpm-lock.yaml").exists()
        ):
            frameworks.add("JavaScript")

    return sorted(frameworks)


def count_dependencies(path: Path):
    package_json = path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            return len(deps) + len(dev_deps)
        except json.JSONDecodeError:
            return 0

    requirements = path / "requirements.txt"
    if requirements.exists():
        return sum(
            1
            for line in requirements.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text()
        return sum(1 for line in text.splitlines() if "dependencies" in line)

    return 0


def is_deployment_ready(path: Path):
    if (path / "Dockerfile").exists() or (
        path / "docker-compose.yml"
    ).exists():
        return True

    workflows = list(path.glob(".github/workflows/*.yml")) + list(
        path.glob(".github/workflows/*.yaml")
    )
    return len(workflows) > 0


def detect_tests(path: Path):
    test_patterns = [
        "test_*.py",
        "*_test.py",
        "pytest.ini",
        "tox.ini",
        "unittest",
    ]
    for pattern in test_patterns:
        if any(path.rglob(pattern)):
            return True
    return False


def create_report(path: Path):
    analysis = analyze_repo(str(path))
    issues = debug_project({"repo": str(path)})["issues_found"]
    return {
        "repository": path.name,
        "status": "scanned",
        "files_found": analysis["files_found"],
        "languages": detect_languages(path),
        "frameworks": detect_frameworks(path),
        "deployment_checks": {
            "docker": (path / "Dockerfile").exists()
            or (path / "docker-compose.yml").exists(),
            "environment_file": (path / ".env").exists(),
            "tests": detect_tests(path),
        },
        "issues": issues,
    }
