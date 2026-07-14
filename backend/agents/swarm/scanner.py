from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Callable


SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
_TOOL_SEVERITY = {
    "ruff": "LOW",
    "mypy": "MEDIUM",
    "bandit": "HIGH",
    "pytest": "HIGH",
    "pylint": "LOW",
    "radon": "MEDIUM",
}
DEFAULT_TOOL_TIMEOUT = 20
MAX_LINE_LENGTH = 100
MAX_BRANCH_COUNT = 20


@dataclass(frozen=True)
class Issue:
    tool: str
    category: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None
    column: int | None = None
    impact_score: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


class SwarmScanner:
    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path).resolve()

    def scan(self) -> dict:
        issues = self._builtin_scan()
        for runner in (
            self._run_ruff,
            self._run_mypy,
            self._run_bandit,
            self._run_pytest,
            self._run_pylint,
            self._run_radon,
        ):
            issues.extend(runner())

        issues.sort(
            key=lambda item: (
                -SEVERITY_ORDER.get(item.severity, 0),
                item.path or "",
                item.line or 0,
                item.tool,
            )
        )
        counts = {level: 0 for level in SEVERITY_ORDER}
        categories: dict[str, int] = {}
        for issue in issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
            categories[issue.category] = categories.get(issue.category, 0) + 1

        return {
            "root_path": str(self.root_path),
            "issue_count": len(issues),
            "severity_counts": counts,
            "categories": categories,
            "issues": [issue.to_dict() for issue in issues],
        }

    def _builtin_scan(self) -> list[Issue]:
        issues: list[Issue] = []
        secret_pattern = re.compile(r"(api[_-]?key|secret|token)\s*=\s*['\"]?[^'\"\s]+", re.IGNORECASE)
        jwt_pattern = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+")
        aws_pattern = re.compile(r"AKIA[0-9A-Z]{16}")
        for path in self.root_path.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            rel_path = str(path.relative_to(self.root_path))
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            lines = content.splitlines()
            if path.suffix in {".py", ".md", ".txt", ".yml", ".yaml", ".ini", ".cfg"}:
                for line_number, line in enumerate(lines, start=1):
                    if "\t" in line or line.rstrip() != line:
                        issues.append(
                            Issue(
                                tool="builtin",
                                category="FORMAT",
                                severity="LOW",
                                message="Whitespace normalization recommended",
                                path=rel_path,
                                line=line_number,
                                impact_score=1,
                            )
                        )
                        break
                    if len(line) > MAX_LINE_LENGTH:
                        issues.append(
                            Issue(
                                tool="builtin",
                                category="LINT",
                                severity="LOW",
                                message="Line exceeds 100 characters",
                                path=rel_path,
                                line=line_number,
                                impact_score=1,
                            )
                        )
                        break

            if (
                path.name == ".env"
                or secret_pattern.search(content)
                or jwt_pattern.search(content)
                or aws_pattern.search(content)
            ):
                issues.append(
                    Issue(
                        tool="builtin",
                        category="SECURITY",
                        severity="HIGH",
                        message="Potential secret-bearing configuration detected",
                        path=rel_path,
                        impact_score=3,
                    )
                )

            if path.suffix == ".py":
                if content.count("if ") + content.count("for ") + content.count("while ") > MAX_BRANCH_COUNT:
                    issues.append(
                        Issue(
                            tool="builtin",
                            category="COMPLEXITY",
                            severity="MEDIUM",
                            message="High branch density detected",
                            path=rel_path,
                            impact_score=2,
                        )
                    )
                if "->" not in content and "def " in content:
                    issues.append(
                        Issue(
                            tool="builtin",
                            category="TYPE_CHECK",
                            severity="LOW",
                            message="Function definitions may benefit from type hints",
                            path=rel_path,
                            impact_score=1,
                        )
                    )
        return issues

    def _tool_issues(
        self,
        tool: str,
        command: list[str],
        parser: Callable[[str], list[Issue]],
    ) -> list[Issue]:
        if not shutil.which(command[0]):
            return []
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.root_path),
                capture_output=True,
                text=True,
                timeout=DEFAULT_TOOL_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []

        output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
        if completed.returncode == 0 and not output.strip():
            return []
        parsed = parser(output)
        if parsed:
            return parsed
        if completed.returncode == 0:
            return []
        return [
            Issue(
                tool=tool,
                category=self._category_for_tool(tool),
                severity=_TOOL_SEVERITY.get(tool, "LOW"),
                message=output.strip().splitlines()[0][:300] or f"{tool} reported issues",
                impact_score=1,
            )
        ]

    def _run_ruff(self) -> list[Issue]:
        return self._tool_issues(
            "ruff",
            ["ruff", "check", "--output-format", "json", "."],
            self._parse_ruff,
        )

    def _run_mypy(self) -> list[Issue]:
        return self._tool_issues(
            "mypy",
            ["mypy", ".", "--hide-error-context", "--no-error-summary"],
            self._parse_mypy,
        )

    def _run_bandit(self) -> list[Issue]:
        return self._tool_issues(
            "bandit",
            ["bandit", "-r", ".", "-f", "json"],
            self._parse_bandit,
        )

    def _run_pytest(self) -> list[Issue]:
        return self._tool_issues(
            "pytest",
            ["pytest", "-q"],
            self._parse_pytest,
        )

    def _run_pylint(self) -> list[Issue]:
        return self._tool_issues(
            "pylint",
            ["pylint", "backend", "--output-format=json"],
            self._parse_pylint,
        )

    def _run_radon(self) -> list[Issue]:
        return self._tool_issues(
            "radon",
            ["radon", "cc", ".", "-j"],
            self._parse_radon,
        )

    def _parse_ruff(self, output: str) -> list[Issue]:
        try:
            payload = json.loads(output or "[]")
        except json.JSONDecodeError:
            return []
        issues = []
        for item in payload:
            location = item.get("location") or {}
            issues.append(
                Issue(
                    tool="ruff",
                    category="LINT",
                    severity="LOW",
                    message=item.get("message", "ruff issue"),
                    path=item.get("filename"),
                    line=location.get("row"),
                    column=location.get("column"),
                    impact_score=1,
                )
            )
        return issues

    def _parse_mypy(self, output: str) -> list[Issue]:
        issues = []
        pattern = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+): (?P<message>.+)$")
        for line in output.splitlines():
            match = pattern.match(line.strip())
            if match:
                issues.append(
                    Issue(
                        tool="mypy",
                        category="TYPE_CHECK",
                        severity="MEDIUM",
                        message=match.group("message"),
                        path=match.group("path"),
                        line=int(match.group("line")),
                        impact_score=2,
                    )
                )
        return issues

    def _parse_bandit(self, output: str) -> list[Issue]:
        try:
            payload = json.loads(output or "{}")
        except json.JSONDecodeError:
            return []
        issues = []
        for item in payload.get("results", []):
            issues.append(
                Issue(
                    tool="bandit",
                    category="SECURITY",
                    severity=(item.get("issue_severity") or "LOW").upper(),
                    message=item.get("issue_text", "bandit finding"),
                    path=item.get("filename"),
                    line=item.get("line_number"),
                    impact_score=3 if (item.get("issue_severity") or "LOW").upper() in {"HIGH", "MEDIUM"} else 1,
                )
            )
        return issues

    def _parse_pytest(self, output: str) -> list[Issue]:
        issues = []
        for line in output.splitlines():
            text = line.strip()
            if text.startswith("FAILED "):
                issues.append(
                    Issue(
                        tool="pytest",
                        category="TEST",
                        severity="HIGH",
                        message=text[:300],
                        impact_score=3,
                    )
                )
        return issues

    def _parse_pylint(self, output: str) -> list[Issue]:
        try:
            payload = json.loads(output or "[]")
        except json.JSONDecodeError:
            return []
        issues = []
        for item in payload:
            issues.append(
                Issue(
                    tool="pylint",
                    category="LINT",
                    severity="LOW",
                    message=item.get("message", "pylint issue"),
                    path=item.get("path"),
                    line=item.get("line"),
                    column=item.get("column"),
                    impact_score=1,
                )
            )
        return issues

    def _parse_radon(self, output: str) -> list[Issue]:
        try:
            payload = json.loads(output or "{}")
        except json.JSONDecodeError:
            return []
        issues = []
        for path, entries in payload.items():
            for entry in entries:
                rank = entry.get("rank", "A")
                if rank in {"A", "B"}:
                    continue
                issues.append(
                    Issue(
                        tool="radon",
                        category="COMPLEXITY",
                        severity="MEDIUM" if rank == "C" else "HIGH",
                        message=f"Complexity rank {rank} for {entry.get('name', 'block')}",
                        path=path,
                        line=entry.get("lineno"),
                        impact_score=2 if rank == "C" else 3,
                    )
                )
        return issues

    def _category_for_tool(self, tool: str) -> str:
        return {
            "ruff": "LINT",
            "mypy": "TYPE_CHECK",
            "bandit": "SECURITY",
            "pytest": "TEST",
            "pylint": "LINT",
            "radon": "COMPLEXITY",
        }.get(tool, "LINT")
