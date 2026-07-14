import time

from backend.agents.swarm.scanner import SwarmScanner
from backend.agents.swarm.task_manager import SwarmTaskManager


def test_swarm_scanner_detects_builtin_issues(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("AI_API_KEY=secret\n")
    (project / "sample.py").write_text("def demo():\n\treturn 1  \n")

    result = SwarmScanner(project).scan()

    categories = {issue["category"] for issue in result["issues"]}
    assert "FORMAT" in categories
    assert "SECURITY" in categories
    assert result["issue_count"] >= 2


def test_task_manager_prefers_higher_priority_change(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    target = project / "sample.py"
    target.write_text("def demo():\n\treturn 1  \n")
    manager = SwarmTaskManager()

    def fake_scan(self):
        return {
            "root_path": str(project),
            "issue_count": 2,
            "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 2},
            "categories": {"FORMAT": 1, "TYPE_CHECK": 1},
            "issues": [
                {"category": "FORMAT", "path": "sample.py", "message": "format"},
                {"category": "TYPE_CHECK", "path": "sample.py", "message": "type"},
            ],
        }

    monkeypatch.setattr("backend.agents.swarm.task_manager.SwarmScanner.scan", fake_scan)
    monkeypatch.setattr(
        "backend.agents.swarm.task_manager.build_agent_pool",
        lambda: {
            "FORMAT": type(
                "FormatStub",
                (),
                {
                    "name": "FormatAgent",
                    "run": lambda self, root, issues: type(
                        "Result",
                        (),
                        {
                            "to_dict": lambda _self: {
                                "agent": "FormatAgent",
                                "status": "completed",
                                "changes": [{"path": "sample.py", "updated": "format\n", "priority": 1, "diff": "format"}],
                            }
                        },
                    )(),
                },
            )(),
            "TYPE_CHECK": type(
                "TypeStub",
                (),
                {
                    "name": "TypeAgent",
                    "run": lambda self, root, issues: type(
                        "Result",
                        (),
                        {
                            "to_dict": lambda _self: {
                                "agent": "TypeAgent",
                                "status": "completed",
                                "changes": [{"path": "sample.py", "updated": "type\n", "priority": 4, "diff": "type"}],
                            }
                        },
                    )(),
                },
            )(),
        },
    )

    task = manager.create_task(project)
    deadline = time.time() + 5
    while time.time() < deadline:
        snapshot = manager.get_task(task["task_id"])
        if snapshot["status"] in {"completed", "completed_with_errors", "failed"}:
            break
    else:
        raise AssertionError("swarm task did not complete in time")

    merged = snapshot["merged_result"]
    assert merged["changes"][0]["updated"] == "type\n"
