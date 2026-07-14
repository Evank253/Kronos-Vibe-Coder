from pathlib import Path

from backend.agents.scan_pipeline import scan_repository


def test_scan_repository_runs_pipeline(monkeypatch, tmp_path):
    fake_repo_dir = tmp_path / "fake-repo"
    fake_repo_dir.mkdir()
    (fake_repo_dir / "README.md").write_text("# Fake Repo\n")

    monkeypatch.setattr(
        "backend.agents.scan_pipeline.clone_repo",
        lambda url: {
            "status": "cloned",
            "repository": "fake-repo",
            "path": str(fake_repo_dir),
        },
    )
    monkeypatch.setattr(
        "backend.agents.scan_pipeline.analyze_repo",
        lambda path: {
            "status": "analysis complete",
            "files_found": 1,
            "files": [str(fake_repo_dir / "README.md")],
        },
    )
    monkeypatch.setattr(
        "backend.agents.scan_pipeline.debug_project",
        lambda data: {
            "status": "debug scan complete",
            "issues_found": [],
            "message": "No errors detected yet",
        },
    )
    monkeypatch.setattr(
        "backend.agents.scan_pipeline.run_tests",
        lambda path: {"tests": "passed", "build": "not tested"},
    )
    monkeypatch.setattr(
        "backend.agents.scan_pipeline.deployment_check",
        lambda path: {
            "deployment_score": "0/5",
            "checks": {},
            "ready": False,
        },
    )
    monkeypatch.setattr(
        "backend.agents.scan_pipeline.security_scan",
        lambda path: {"security_findings": [], "status": "scanned"},
    )
    monkeypatch.setattr(
        "backend.agents.scan_pipeline.review_codebase",
        lambda report: {
            "review_status": "complete",
            "recommendations": [],
            "next_action": "Run debug and deployment agents",
        },
    )
    monkeypatch.setattr(
        "backend.agents.scan_pipeline.generate_report",
        lambda data: {"report": data, "status": "complete"},
    )

    result = scan_repository("https://github.com/example/fake-repo")

    assert result["status"] == "complete"
    assert result["report"]["repository"]["repository"] == "fake-repo"
    assert result["report"]["analysis"]["files_found"] == 1
    assert result["report"]["debug"]["issues_found"] == []
