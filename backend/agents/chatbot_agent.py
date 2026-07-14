"""AI chatbot agent for code analysis and fix suggestions.

Uses an OpenAI-compatible API (configurable via environment variables).
Falls back to a rule-based summary when no API key is configured.
"""

import os
import subprocess
from pathlib import Path


def _call_llm(system: str, user: str) -> str:
    """Call the configured LLM provider.

    Environment variables:
      AI_BASE_URL  – OpenAI-compatible base URL (default: https://api.openai.com/v1)
      AI_API_KEY   – API key (required for real calls)
      AI_MODEL     – model name (default: gpt-4o-mini)
    """
    api_key = os.getenv("AI_API_KEY", "")
    if not api_key:
        return "[AI suggestions unavailable: set AI_API_KEY to enable LLM responses]"

    try:
        import urllib.request
        import json

        base_url = os.getenv(
            "AI_BASE_URL", "https://api.openai.com/v1"
        ).rstrip("/")
        model = os.getenv("AI_MODEL", "gpt-4o-mini")
        payload = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 1024,
            }
        ).encode()

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"[LLM call failed: {exc}]"


def _run_ruff(path: str) -> dict:
    """Run ruff lint on the given path and return findings."""
    try:
        result = subprocess.run(
            ["ruff", "check", path, "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        import json

        issues = json.loads(result.stdout) if result.stdout.strip() else []
        return {"tool": "ruff", "issues": issues, "count": len(issues)}
    except FileNotFoundError:
        return {
            "tool": "ruff",
            "issues": [],
            "count": 0,
            "error": "ruff not installed",
        }
    except Exception as exc:
        return {"tool": "ruff", "issues": [], "count": 0, "error": str(exc)}


def _run_pytest(path: str) -> dict:
    """Run pytest on the given path and return a summary."""
    try:
        result = subprocess.run(
            ["pytest", path, "-q", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=path,
        )
        return {
            "tool": "pytest",
            "returncode": result.returncode,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-1000:],
            "passed": result.returncode == 0,
        }
    except FileNotFoundError:
        return {"tool": "pytest", "error": "pytest not installed"}
    except Exception as exc:
        return {"tool": "pytest", "error": str(exc)}


def analyze_path(path: str) -> dict:
    """Run all available checks on a local path and return a summary."""
    p = Path(path)
    if not p.exists():
        return {"error": f"Path not found: {path}"}

    lint = _run_ruff(path)
    tests = _run_pytest(path) if p.is_dir() else {}

    # collect file list
    files = []
    if p.is_dir():
        for fp in sorted(p.rglob("*.py")):
            files.append(str(fp.relative_to(p)))

    summary_parts = []
    if lint.get("count", 0):
        summary_parts.append(f"Ruff found {lint['count']} lint issue(s).")
    else:
        summary_parts.append("No Ruff lint issues found.")

    if tests:
        if tests.get("passed"):
            summary_parts.append("All tests passed.")
        elif "error" in tests:
            summary_parts.append(f"Tests could not run: {tests['error']}")
        else:
            summary_parts.append("Some tests failed.")

    return {
        "path": path,
        "python_files": files,
        "lint": lint,
        "tests": tests,
        "summary": " ".join(summary_parts),
    }


def suggest_fixes(analysis: dict) -> dict:
    """Given an analysis result, produce fix suggestions via LLM."""
    lint = analysis.get("lint", {})
    tests = analysis.get("tests", {})
    summary = analysis.get("summary", "")

    # Build a compact problem description
    issues_text = ""
    for issue in lint.get("issues", [])[:20]:
        loc = f"{issue.get('filename', '?')}:{issue.get('location', {}).get('row', '?')}"
        code = issue.get("code", "?")
        msg = issue.get("message", "")
        issues_text += f"  {loc} [{code}] {msg}\n"

    test_output = tests.get("stdout", "")[:1500]

    user_prompt = f"""Repository analysis summary:
{summary}

Lint issues (up to 20 shown):
{issues_text or "  None"}

Test output:
{test_output or "  Not available"}

Please:
1. Explain each class of error in plain language.
2. Show a concrete fix for the most common issue with a before/after code snippet.
3. List any patterns that suggest deeper architectural problems.
4. Suggest 3 quick-win improvements the developer can apply today.
"""

    system_prompt = (
        "You are an expert Python code-review assistant. "
        "Give concise, actionable advice. Use markdown formatting."
    )

    suggestion = _call_llm(system_prompt, user_prompt)

    return {
        "analysis_summary": summary,
        "suggestions": suggestion,
        "lint_count": lint.get("count", 0),
        "tests_passed": tests.get("passed"),
    }
