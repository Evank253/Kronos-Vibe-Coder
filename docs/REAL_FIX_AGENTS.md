# Real Fix Agents (Kronos-Vibe-Coder)

## What changed

Previously `fix_agent` only simulated whitespace cleanup and never drove real GitHub commits of fixed source.

Now:

1. **`generate_fix_plan_for_path`** produces real before/after content for:
   - Tabs → 4 spaces, trailing whitespace, EOF newline
   - Bare `except:` → `except Exception:`
   - Notes Python files that fail AST parse (`syntax_errors`)
2. **`apply_fix_plan(..., target_root=...)`** writes the fixed content to disk
3. **`fixes_to_commit_changes`** formats the plan for `github_manager.commit_changes`
4. **`fix_pipeline.run_fix_pipeline`** orchestrates plan → local apply → branch → commit → PR

## Usage

```python
from backend.agents.fix_pipeline import run_fix_pipeline

result = run_fix_pipeline(
    local_path="/tmp/cloned-repo",
    repo_full_name="owner/repo",
    base_branch="main",
    apply_locally=True,
    open_pr=True,
    token=os.environ["GITHUB_TOKEN"],
)
print(result["status"], result.get("github"))
```

## Safety

- Only applies transforms that keep valid Python parseable when the original was parseable
- Skips `.git`, `node_modules`, venvs, build dirs
- PR body asks for human review before merge

## Next extensions

- LLM-backed semantic fixes (opt-in)
- Test-aware fixes (run pytest after apply, revert on failure)
- Provenance record via Integration Layer after each successful PR
