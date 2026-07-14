from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
import uuid

from backend.agents.swarm.agent_pool import build_agent_pool
from backend.agents.swarm.executor import SwarmExecutor
from backend.agents.swarm.scanner import SwarmScanner


class SwarmTaskManager:
    def __init__(self, executor: SwarmExecutor | None = None):
        self.executor = executor or SwarmExecutor()
        self._tasks: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create_task(self, root_path: str | Path) -> dict:
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "root_path": str(Path(root_path).resolve()),
            "status": "queued",
            "created_at": self._now(),
            "updated_at": self._now(),
            "events": [self._event("queued", "Task queued")],
            "scan": None,
            "agent_results": {},
            "merged_result": {"files": [], "diffs": [], "changes": []},
            "summary": {"issues_remaining": 0, "fixes_applied": 0, "agents_total": 0, "agents_completed": 0},
            "errors": [],
        }
        with self._lock:
            self._tasks[task_id] = task
        thread = threading.Thread(target=self._run_task, args=(task_id,), daemon=True)
        thread.start()
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return None if task is None else self._snapshot(task)

    def finalize(self, task_id: str, write_files: bool = False) -> dict:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(task_id)
            merged = task["merged_result"]
            root_path = Path(task["root_path"])
            if write_files:
                for change in merged["changes"]:
                    file_path = root_path / change["path"]
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(change["updated"], encoding="utf-8")
                task["events"].append(self._event("merged", "Merged changes written to disk"))
                task["updated_at"] = self._now()
            return {
                "task_id": task_id,
                "status": task["status"],
                "written": write_files,
                "merged_result": merged,
            }

    def _run_task(self, task_id: str) -> None:
        self._update(task_id, status="running", event=self._event("scan", "Running swarm scan"))
        task = self.get_task(task_id)
        if task is None:
            return
        scanner = SwarmScanner(task["root_path"])
        try:
            scan_result = scanner.scan()
            grouped = self._group_by_category(scan_result.get("issues", []))
            self._update(
                task_id,
                scan=scan_result,
                summary={
                    "issues_remaining": scan_result.get("issue_count", 0),
                    "fixes_applied": 0,
                    "agents_total": len(grouped),
                    "agents_completed": 0,
                },
                event=self._event("dispatch", "Dispatching agents"),
            )
            pool = build_agent_pool()
            jobs = []
            for category, issues in grouped.items():
                agent = pool.get(category)
                if not agent:
                    continue
                jobs.append((agent.name, lambda a=agent, i=issues: a.run(task["root_path"], i).to_dict()))
            results = self.executor.run(jobs)
            merged = self._merge_results(results)
            summary = {
                "issues_remaining": max(scan_result.get("issue_count", 0) - len(merged["changes"]), 0),
                "fixes_applied": len(merged["changes"]),
                "agents_total": len(jobs),
                "agents_completed": sum(1 for result in results.values() if result.get("status") == "completed"),
            }
            errors = [result.get("error") for result in results.values() if result.get("error")]
            self._update(
                task_id,
                status="completed" if not errors else "completed_with_errors",
                agent_results=results,
                merged_result=merged,
                summary=summary,
                errors=errors,
                event=self._event("complete", "Swarm execution finished"),
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._update(
                task_id,
                status="failed",
                errors=[str(exc)],
                event=self._event("failed", f"Swarm execution failed: {exc}"),
            )

    def _merge_results(self, results: dict[str, dict]) -> dict:
        selected: dict[str, dict] = {}
        diffs: list[str] = []
        for result in results.values():
            for change in result.get("changes", []):
                current = selected.get(change["path"])
                if current is None or change.get("priority", 0) > current.get("priority", 0):
                    selected[change["path"]] = change
        ordered_changes = [selected[path] for path in sorted(selected)]
        diffs.extend(change.get("diff", "") for change in ordered_changes if change.get("diff"))
        return {
            "files": list(selected),
            "diffs": diffs,
            "changes": ordered_changes,
        }

    def _group_by_category(self, issues: list[dict]) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for issue in issues:
            grouped.setdefault(issue.get("category", "LINT"), []).append(issue)
        return grouped

    def _update(self, task_id: str, event: dict | None = None, **changes: dict) -> None:
        with self._lock:
            task = self._tasks[task_id]
            task.update(changes)
            task["updated_at"] = self._now()
            if event:
                task["events"].append(event)

    def _snapshot(self, task: dict) -> dict:
        copy = dict(task)
        copy["events"] = list(task.get("events", []))
        copy["agent_results"] = dict(task.get("agent_results", {}))
        copy["merged_result"] = dict(task.get("merged_result", {}))
        copy["summary"] = dict(task.get("summary", {}))
        copy["errors"] = list(task.get("errors", []))
        return copy

    def _event(self, stage: str, message: str) -> dict:
        return {"stage": stage, "message": message, "timestamp": self._now()}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
