from .repo_analyzer import analyze_repo
from .debug_agent import debug_project
from .github_agent import clone_repo
from .test_agent import run_tests
from .deploy_agent import deployment_check
from .security_agent import security_scan
from .ai_review_agent import review_codebase
from .report_agent import generate_report


def scan_repository(repo_url: str):
    repo = clone_repo(repo_url)
    if repo.get("status") == "error":
        return {
            "status": "error",
            "error": repo.get("error"),
            "repository": repo,
            "path": repo.get("path"),
        }

    path = repo["path"]
    analysis = analyze_repo(path)
    debug_result = debug_project({"repo": path})
    tests = run_tests(path)
    deployment = deployment_check(path)
    security = security_scan(path)
    ai_review = review_codebase({"analysis": analysis})

    report = generate_report({
        "repository": repo,
        "analysis": analysis,
        "debug": debug_result,
        "tests": tests,
        "deployment": deployment,
        "security": security,
        "ai_review": ai_review,
        "path": path,
    })
    # Ensure top-level path for fix_agent / workers
    if isinstance(report, dict):
        report["path"] = path
    return report
