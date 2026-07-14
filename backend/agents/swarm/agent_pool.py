from __future__ import annotations

from dataclasses import dataclass
import difflib
from pathlib import Path
from typing import Iterable

from backend.agents.fix_agent import _normalize_text


AGENT_PRIORITY = {
    "TYPE_CHECK": 4,
    "SECURITY": 3,
    "LINT": 2,
    "FORMAT": 1,
    "TEST": 1,
    "COMPLEXITY": 1,
}
AGENT_TYPES = ["LINT", "FORMAT", "TEST", "SECURITY", "TYPE_CHECK", "COMPLEXITY"]


@dataclass
class AgentResult:
    agent: str
    category: str
    status: str
    issue_count: int
    applied_count: int
    changes: list[dict]
    diagnostics: list[str]

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "category": self.category,
            "status": self.status,
            "issue_count": self.issue_count,
            "applied_count": self.applied_count,
            "changes": self.changes,
            "diagnostics": self.diagnostics,
        }


class BaseSwarmAgent:
    def __init__(self, category: str, name: str):
        self.category = category
        self.name = name
        self.priority = AGENT_PRIORITY.get(category, 0)

    def run(self, root_path: str | Path, issues: Iterable[dict]) -> AgentResult:
        issue_list = list(issues)
        changes, diagnostics = self._build_changes(Path(root_path), issue_list)
        return AgentResult(
            agent=self.name,
            category=self.category,
            status="completed",
            issue_count=len(issue_list),
            applied_count=len(changes),
            changes=changes,
            diagnostics=diagnostics,
        )

    def _build_changes(self, root_path: Path, issues: list[dict]) -> tuple[list[dict], list[str]]:
        return [], [f"{self.name} analyzed {len(issues)} issues"]

    def _change(self, path: str, original: str, updated: str) -> dict:
        diff = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        return {
            "path": path,
            "updated": updated,
            "priority": self.priority,
            "agent": self.name,
            "diff": diff,
        }


class FormatAgent(BaseSwarmAgent):
    def _build_changes(self, root_path: Path, issues: list[dict]) -> tuple[list[dict], list[str]]:
        changes = []
        seen_paths = set()
        for issue in issues:
            rel_path = issue.get("path")
            if not rel_path or rel_path in seen_paths:
                continue
            file_path = root_path / rel_path
            if not file_path.exists() or not file_path.is_file():
                continue
            original = file_path.read_text(encoding="utf-8", errors="ignore")
            updated = _normalize_text(original)
            if updated != original:
                changes.append(self._change(rel_path, original, updated))
                seen_paths.add(rel_path)
        return changes, [f"Normalized formatting in {len(changes)} files"]


class LintAgent(FormatAgent):
    pass


class TypeAgent(BaseSwarmAgent):
    def _build_changes(self, root_path: Path, issues: list[dict]) -> tuple[list[dict], list[str]]:
        diagnostics = []
        for issue in issues:
            path = issue.get("path") or "<unknown>"
            diagnostics.append(f"Review typing guidance for {path}: {issue.get('message', 'type issue')}")
        return [], diagnostics or ["No type issues assigned"]


class SecurityAgent(BaseSwarmAgent):
    def _build_changes(self, root_path: Path, issues: list[dict]) -> tuple[list[dict], list[str]]:
        diagnostics = []
        for issue in issues:
            diagnostics.append(f"Security review required for {issue.get('path') or '<unknown>'}")
        return [], diagnostics or ["No security issues assigned"]


class TestAgent(BaseSwarmAgent):
    def _build_changes(self, root_path: Path, issues: list[dict]) -> tuple[list[dict], list[str]]:
        return [], [issue.get("message", "test issue") for issue in issues] or ["No test failures assigned"]


class ComplexityAgent(BaseSwarmAgent):
    def _build_changes(self, root_path: Path, issues: list[dict]) -> tuple[list[dict], list[str]]:
        return [], [issue.get("message", "complexity issue") for issue in issues] or ["No complexity issues assigned"]


def build_agent_pool() -> dict[str, BaseSwarmAgent]:
    return {
        "LINT": LintAgent("LINT", "LintAgent"),
        "FORMAT": FormatAgent("FORMAT", "FormatAgent"),
        "TEST": TestAgent("TEST", "TestAgent"),
        "SECURITY": SecurityAgent("SECURITY", "SecurityAgent"),
        "TYPE_CHECK": TypeAgent("TYPE_CHECK", "TypeAgent"),
        "COMPLEXITY": ComplexityAgent("COMPLEXITY", "ComplexityAgent"),
    }
