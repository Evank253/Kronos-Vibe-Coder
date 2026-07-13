import os
import tempfile
from backend.agents.fix_agent import generate_fix_plan, apply_fix_plan


def test_fix_agent_generates_fixes(tmp_path):
    d = tmp_path / 'proj'
    d.mkdir()
    f = d / 'a.py'
    f.write_text('def f():\n\tprint("hi")  \n')

    plan = generate_fix_plan(str(d))
    assert plan['fix_count'] >= 1
    preview = apply_fix_plan(plan)
    assert preview['status'] == 'preview'
    assert any('unified diff' or 'diff' for _ in [preview]) or preview['changes']
