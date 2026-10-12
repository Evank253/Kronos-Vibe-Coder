"""Tests that fix_agent performs real file mutations and safe Python rewrites."""
import os
from backend.agents.fix_agent import (
    generate_fix_plan,
    apply_fix_plan,
    fixes_to_commit_changes,
)


def test_whitespace_and_bare_except_real_write(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    src = proj / "mod.py"
    src.write_text("def f():\n\tprint(\"hi\")  \n    try:\n        x = 1\n    except:\n        pass\n")

    plan = generate_fix_plan(str(proj))
    assert plan["fix_count"] >= 1
    assert any("bare_except" in (f.get("tags") or []) or "whitespace_normalize" in (f.get("tags") or [])
               for f in plan["fixes"])

    result = apply_fix_plan(plan, target_root=str(proj))
    assert result["status"] == "applied"
    text = src.read_text()
    assert "\t" not in text
    assert "except Exception:" in text
    assert text.endswith("\n")


def test_fixes_to_commit_changes_shape(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1  \n")
    plan = generate_fix_plan(str(proj))
    changes = fixes_to_commit_changes(plan)
    assert isinstance(changes, list)
    if changes:
        assert "path" in changes[0] and "content" in changes[0]
